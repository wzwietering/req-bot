import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import joinedload, sessionmaker

from .database_models import Base  # SQLAlchemy ORM models
from .database_models import (
    AnswerTable,
    QuestionTable,
    RequirementTable,
    SessionTable,
    enable_sqlite_foreign_keys,
)
from .models import Answer, Question, Requirement, Session  # Pydantic models
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

        # Create tables
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

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session to prevent race conditions."""
        with self._lock_manager_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.Lock()
            return self._session_locks[session_id]

    def save_session(self, session: Session) -> str:
        """Save a session to the database using upsert patterns. Returns session ID."""
        session_lock = self._get_session_lock(session.id)

        with session_lock:
            with self.SessionLocal() as db_session:
                try:
                    # Update timestamp
                    session.updated_at = datetime.now(UTC)

                    # Upsert session record
                    session_table = SessionTable(
                        id=session.id,
                        project=session.project,
                        conversation_complete=session.conversation_complete,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                    )
                    merged_session = db_session.merge(session_table)

                    # Get existing related records for comparison
                    existing_questions = {q.id: q for q in merged_session.questions}
                    existing_answers = {
                        a.question_id: a for a in merged_session.answers
                    }
                    existing_requirements = {
                        r.id: r for r in merged_session.requirements
                    }

                    # Upsert questions
                    current_question_ids: set[str] = set()
                    for i, question in enumerate(session.questions):
                        current_question_ids.add(question.id)
                        if question.id in existing_questions:
                            # Update existing question
                            existing_q = existing_questions[question.id]
                            existing_q.text = question.text
                            existing_q.category = question.category
                            existing_q.required = question.required
                            existing_q.order_index = i
                        else:
                            # Add new question
                            q_table = QuestionTable(
                                id=question.id,
                                session_id=session.id,
                                text=question.text,
                                category=question.category,
                                required=question.required,
                                order_index=i,
                            )
                            db_session.add(q_table)

                    # Remove questions that are no longer present
                    for q_id, existing_q in existing_questions.items():
                        if q_id not in current_question_ids:
                            db_session.delete(existing_q)

                    # Upsert answers
                    current_answer_q_ids: set[str] = set()
                    for answer in session.answers:
                        current_answer_q_ids.add(answer.question_id)
                        if answer.question_id in existing_answers:
                            # Update existing answer
                            existing_a = existing_answers[answer.question_id]
                            existing_a.text = answer.text
                            existing_a.is_vague = answer.is_vague
                            existing_a.needs_followup = answer.needs_followup
                        else:
                            # Add new answer
                            a_table = AnswerTable(
                                session_id=session.id,
                                question_id=answer.question_id,
                                text=answer.text,
                                is_vague=answer.is_vague,
                                needs_followup=answer.needs_followup,
                            )
                            db_session.add(a_table)

                    # Remove answers that are no longer present
                    for q_id, existing_a in existing_answers.items():
                        if q_id not in current_answer_q_ids:
                            db_session.delete(existing_a)

                    # Upsert requirements
                    current_requirement_ids: set[str] = set()
                    for i, requirement in enumerate(session.requirements):
                        current_requirement_ids.add(requirement.id)
                        if requirement.id in existing_requirements:
                            # Update existing requirement
                            existing_r = existing_requirements[requirement.id]
                            existing_r.title = requirement.title
                            existing_r.rationale = requirement.rationale
                            existing_r.priority = requirement.priority
                            existing_r.order_index = i
                        else:
                            # Add new requirement
                            r_table = RequirementTable(
                                id=requirement.id,
                                session_id=session.id,
                                title=requirement.title,
                                rationale=requirement.rationale,
                                priority=requirement.priority,
                                order_index=i,
                            )
                            db_session.add(r_table)

                    # Remove requirements that are no longer present
                    for r_id, existing_r in existing_requirements.items():
                        if r_id not in current_requirement_ids:
                            db_session.delete(existing_r)

                    db_session.commit()
                    return session.id

                except Exception as e:
                    db_session.rollback()
                    raise SessionSaveError(
                        f"Failed to save session {session.id}: {str(e)}"
                    ) from e

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from the database using eager loading to avoid N+1 queries."""
        session_id = self._validate_session_id(session_id)
        with self.SessionLocal() as db_session:
            try:
                # Use eager loading to fetch session with all related data in a single query
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
                session_table = result.scalar_one_or_none()

                if not session_table:
                    return None

                # Sort questions and requirements by order_index
                questions_sorted = sorted(
                    session_table.questions, key=lambda q: q.order_index
                )
                requirements_sorted = sorted(
                    session_table.requirements, key=lambda r: r.order_index
                )

                questions = [
                    Question(
                        id=q.id, text=q.text, category=q.category, required=q.required
                    )
                    for q in questions_sorted
                ]

                answers = [
                    Answer(
                        question_id=a.question_id,
                        text=a.text,
                        is_vague=a.is_vague,
                        needs_followup=a.needs_followup,
                    )
                    for a in session_table.answers
                ]

                requirements = [
                    Requirement(
                        id=r.id,
                        title=r.title,
                        rationale=r.rationale,
                        priority=r.priority,
                    )
                    for r in requirements_sorted
                ]

                return Session(
                    id=session_table.id,
                    project=session_table.project,
                    questions=questions,
                    answers=answers,
                    requirements=requirements,
                    conversation_complete=session_table.conversation_complete,
                    created_at=session_table.created_at,
                    updated_at=session_table.updated_at,
                )

            except Exception as e:
                raise SessionLoadError(
                    f"Failed to load session {session_id}: {str(e)}"
                ) from e

    def list_sessions(self) -> list[tuple[str, str, datetime, bool]]:
        """List all sessions. Returns (id, project, updated_at, conversation_complete)."""
        with self.SessionLocal() as db_session:
            try:
                sessions_query = select(SessionTable).order_by(
                    SessionTable.updated_at.desc()
                )
                sessions = db_session.execute(sessions_query).scalars().all()

                return [
                    (s.id, s.project, s.updated_at, s.conversation_complete)
                    for s in sessions
                ]

            except Exception as e:
                raise StorageError(f"Failed to list sessions: {str(e)}") from e

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from the database. Returns True if deleted, False if not found."""
        session_id = self._validate_session_id(session_id)
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
                raise SessionDeleteError(
                    f"Failed to delete session {session_id}: {str(e)}"
                ) from e
