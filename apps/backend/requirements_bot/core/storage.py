import re
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import joinedload, sessionmaker

from .database_models import (
    AnswerTable,
    Base,  # SQLAlchemy ORM models
    QuestionTable,
    RequirementTable,
    SessionTable,
    enable_sqlite_foreign_keys,
)
from .logging import span
from .models import Session  # Pydantic models
from .persistence.session_persistence_service import SessionPersistenceService
from .storage_interface import StorageInterface


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class SessionNotFoundError(StorageError):
    """Raised when a session cannot be found."""

    pass


class SessionSaveError(StorageError):
    """Raised when a session cannot be saved."""

    pass


class SessionLoadError(StorageError):
    """Raised when a session cannot be loaded."""

    pass


class SessionDeleteError(StorageError):
    """Raised when a session cannot be deleted."""

    pass


class DatabaseManager(StorageInterface):
    def __init__(self, db_path: str = "requirements_bot.db"):
        """Initialize database manager with SQLite database."""
        self.db_path = self._validate_db_path(db_path)
        self._session_locks: dict[str, threading.Lock] = {}
        self._lock_manager_lock = threading.Lock()
        self.persistence_service = SessionPersistenceService()

        # Create database directory if it doesn't exist
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create engine and session factory with connection pooling
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Enable foreign key constraints for SQLite
        enable_sqlite_foreign_keys(self.engine)

        # Only create tables if not managed by Alembic migrations
        # Check if alembic_version table exists to determine if database is migration-managed
        inspector = inspect(self.engine)
        if "alembic_version" not in inspector.get_table_names():
            # Database not managed by alembic, create tables directly
            # This maintains backward compatibility for development/test scenarios
            Base.metadata.create_all(bind=self.engine)

    def _validate_db_path(self, db_path: str) -> str:
        """Validate database path to prevent path traversal attacks."""
        try:
            resolved = Path(db_path).resolve()
            current_dir = Path.cwd().resolve()

            # Ensure the resolved path is within the current working directory or its subdirectories
            if not str(resolved).startswith(str(current_dir)):
                raise ValueError("Database path outside working directory not allowed")

            return str(resolved)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid database path: {e}")

    def _validate_session_id(self, session_id: str) -> str:
        """Validate session ID format to prevent injection attacks."""
        if not re.match(r"^[a-f0-9-]{36}$", session_id):
            raise ValueError("Invalid session ID format")
        return session_id

    def _fetch_session_with_relations(self, db_session, session_id: str):
        """Fetch session table with all related data using eager loading."""
        query = (
            select(SessionTable)
            .options(
                joinedload(SessionTable.questions),
                joinedload(SessionTable.answers),
                joinedload(SessionTable.requirements),
            )
            .where(SessionTable.id == session_id)
        )
        result = db_session.execute(query).unique()
        return result.scalar_one_or_none()

    def _build_session_from_table(self, session_table) -> Session:
        """Build Session object from database table using persistence service."""
        return self.persistence_service.build_session_from_table(session_table)

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session to prevent race conditions."""
        with self._lock_manager_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.Lock()
            return self._session_locks[session_id]

    def save_session(self, session: Session) -> str:
        """Save a session to the database using upsert patterns. Returns session ID."""
        session_lock = self._get_session_lock(session.id)
        with span(
            "db.save_session",
            component="db",
            operation="save_session",
            session_id=session.id,
            questions=len(session.questions),
            answers=len(session.answers),
            requirements=len(session.requirements),
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with session_lock:
                with self.SessionLocal() as db_session:
                    try:
                        result = self.persistence_service.save_session_data(session, db_session)
                        db_session.commit()
                        return result

                    except Exception as e:
                        db_session.rollback()
                        raise SessionSaveError(f"Failed to save session {session.id}: {str(e)}") from e

    def load_session(self, session_id: str) -> Session | None:
        """Load a session from the database using eager loading to avoid N+1 queries."""
        session_id = self._validate_session_id(session_id)
        with span(
            "db.load_session",
            component="db",
            operation="load_session",
            session_id=session_id,
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with self.SessionLocal() as db_session:
                try:
                    session_table = self._fetch_session_with_relations(db_session, session_id)
                    if not session_table:
                        return None
                    return self._build_session_from_table(session_table)
                except Exception as e:
                    raise SessionLoadError(f"Failed to load session {session_id}: {str(e)}") from e

    def list_sessions(self) -> list[tuple[str, str, datetime, bool]]:
        """List all sessions. Returns (id, project, updated_at, conversation_complete)."""
        with span(
            "db.list_sessions",
            component="db",
            operation="list_sessions",
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with self.SessionLocal() as db_session:
                try:
                    sessions_query = select(SessionTable).order_by(SessionTable.updated_at.desc())
                    sessions = db_session.execute(sessions_query).scalars().all()

                    return [(s.id, s.project, s.updated_at, s.conversation_complete) for s in sessions]

                except Exception as e:
                    raise StorageError(f"Failed to list sessions: {str(e)}") from e

    def get_session_summaries(self) -> list[tuple[str, str, str, bool, int, int, int, datetime, datetime]]:
        """Get session summaries in a single optimized query.

        Returns: List of tuples containing (id, project, conversation_state, conversation_complete,
                questions_count, answers_count, requirements_count, created_at, updated_at)
        """
        with span(
            "db.get_session_summaries",
            component="db",
            operation="get_session_summaries",
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with self.SessionLocal() as db_session:
                try:
                    # Single query with left joins and aggregations to avoid N+1 problem
                    query = (
                        select(
                            SessionTable.id,
                            SessionTable.project,
                            SessionTable.conversation_state,
                            SessionTable.conversation_complete,
                            func.count(func.distinct(QuestionTable.id)).label("questions_count"),
                            func.count(func.distinct(AnswerTable.id)).label("answers_count"),
                            func.count(func.distinct(RequirementTable.id)).label("requirements_count"),
                            SessionTable.created_at,
                            SessionTable.updated_at,
                        )
                        .outerjoin(QuestionTable, SessionTable.id == QuestionTable.session_id)
                        .outerjoin(AnswerTable, SessionTable.id == AnswerTable.session_id)
                        .outerjoin(RequirementTable, SessionTable.id == RequirementTable.session_id)
                        .group_by(SessionTable.id)
                        .order_by(SessionTable.updated_at.desc())
                    )

                    result = db_session.execute(query).all()
                    return [
                        (
                            row.id,
                            row.project,
                            row.conversation_state,
                            row.conversation_complete,
                            row.questions_count,
                            row.answers_count,
                            row.requirements_count,
                            row.created_at,
                            row.updated_at,
                        )
                        for row in result
                    ]

                except Exception as e:
                    raise StorageError(f"Failed to get session summaries: {str(e)}") from e

    def get_session_summaries_for_user(
        self, user_id: str
    ) -> list[tuple[str, str, str, bool, int, int, int, datetime, datetime]]:
        """Get session summaries for a specific user.

        Args:
            user_id: ID of the user to filter sessions for

        Returns: List of tuples containing (id, project, conversation_state, conversation_complete,
                questions_count, answers_count, requirements_count, created_at, updated_at)
        """
        with span(
            "db.get_session_summaries_for_user",
            component="db",
            operation="get_session_summaries_for_user",
            user_id=user_id,
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with self.SessionLocal() as db_session:
                try:
                    # Single query with left joins and aggregations, filtered by user
                    query = (
                        select(
                            SessionTable.id,
                            SessionTable.project,
                            SessionTable.conversation_state,
                            SessionTable.conversation_complete,
                            func.count(func.distinct(QuestionTable.id)).label("questions_count"),
                            func.count(func.distinct(AnswerTable.id)).label("answers_count"),
                            func.count(func.distinct(RequirementTable.id)).label("requirements_count"),
                            SessionTable.created_at,
                            SessionTable.updated_at,
                        )
                        .outerjoin(QuestionTable, SessionTable.id == QuestionTable.session_id)
                        .outerjoin(AnswerTable, SessionTable.id == AnswerTable.session_id)
                        .outerjoin(RequirementTable, SessionTable.id == RequirementTable.session_id)
                        .where(SessionTable.user_id == user_id)
                        .group_by(SessionTable.id)
                        .order_by(SessionTable.updated_at.desc())
                    )

                    result = db_session.execute(query).all()
                    return [
                        (
                            row.id,
                            row.project,
                            row.conversation_state,
                            row.conversation_complete,
                            row.questions_count,
                            row.answers_count,
                            row.requirements_count,
                            row.created_at,
                            row.updated_at,
                        )
                        for row in result
                    ]

                except Exception as e:
                    raise StorageError(f"Failed to get session summaries for user {user_id}: {str(e)}") from e

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the database. Returns True if deleted, False if not found."""
        session_id = self._validate_session_id(session_id)
        with span(
            "db.delete_session",
            component="db",
            operation="delete_session",
            session_id=session_id,
            db_engine="sqlite",
            db_path=Path(self.db_path).name,
        ):
            with self.SessionLocal() as db_session:
                try:
                    session_table = db_session.get(SessionTable, session_id)
                    if not session_table:
                        return False

                    db_session.delete(session_table)
                    db_session.commit()
                    return True

                except Exception as e:
                    db_session.rollback()
                    raise SessionDeleteError(f"Failed to delete session {session_id}: {str(e)}") from e

    def close(self) -> None:
        """Close the database engine and clean up resources."""
        try:
            if hasattr(self, "engine") and self.engine:
                self.engine.dispose()
        except Exception:
            # Log error if needed, but don't raise to avoid masking other exceptions
            pass
