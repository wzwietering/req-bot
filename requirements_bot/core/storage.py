import json
import logging
import re
import threading
from datetime import UTC, datetime
from pathlib import Path

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
from .logging import span
from .conversation_state import ConversationState, StateContext
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
        """Build Session object from database table with proper sorting."""
        questions = self._convert_questions_from_table(session_table)
        answers = self._convert_answers_from_table(session_table)
        requirements = self._convert_requirements_from_table(session_table)
        state_context = self._deserialize_state_context(session_table.state_context)

        return Session(
            id=session_table.id,
            project=session_table.project,
            questions=questions,
            answers=answers,
            requirements=requirements,
            conversation_complete=session_table.conversation_complete,
            created_at=session_table.created_at,
            updated_at=session_table.updated_at,
            conversation_state=ConversationState(session_table.conversation_state),
            state_context=state_context,
            last_state_change=session_table.last_state_change
            or session_table.updated_at,
        )

    def _convert_questions_from_table(self, session_table) -> list:
        """Convert database question records to Question objects."""
        questions_sorted = sorted(session_table.questions, key=lambda q: q.order_index)
        return [
            Question(
                id=q.id,
                text=q.text,
                category=q.category,
                required=q.required,
            )
            for q in questions_sorted
        ]

    def _convert_answers_from_table(self, session_table) -> list:
        """Convert database answer records to Answer objects."""
        return [
            Answer(
                question_id=a.question_id,
                text=a.text,
                is_vague=a.is_vague,
                needs_followup=a.needs_followup,
            )
            for a in session_table.answers
        ]

    def _convert_requirements_from_table(self, session_table) -> list:
        """Convert database requirement records to Requirement objects."""
        requirements_sorted = sorted(
            session_table.requirements, key=lambda r: r.order_index
        )
        return [
            Requirement(
                id=r.id,
                title=r.title,
                rationale=r.rationale,
                priority=r.priority,
            )
            for r in requirements_sorted
        ]

    def _deserialize_state_context(self, context_json: str | None) -> StateContext:
        """Deserialize state context from JSON with fallback to default."""
        if not context_json:
            return StateContext()

        try:
            context_data = json.loads(context_json)
            return StateContext.model_validate(context_data)
        except (json.JSONDecodeError, ValueError):
            return StateContext()

    def _get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session to prevent race conditions."""
        with self._lock_manager_lock:
            if session_id not in self._session_locks:
                self._session_locks[session_id] = threading.Lock()
            return self._session_locks[session_id]

    def _update_session_metadata(self, session: Session) -> None:
        """Update session timestamps."""
        session.updated_at = datetime.now(UTC)

    def _serialize_state_context(self, session: Session) -> str:
        """Serialize state context to JSON."""
        return json.dumps(session.state_context.model_dump())

    def _upsert_session_record(
        self, session: Session, db_session, state_context_json: str
    ):
        """Upsert the main session record."""
        session_table = SessionTable(
            id=session.id,
            project=session.project,
            conversation_complete=session.conversation_complete,
            created_at=session.created_at,
            updated_at=session.updated_at,
            conversation_state=session.conversation_state.value,
            state_context=state_context_json,
            last_state_change=session.last_state_change,
        )
        return db_session.merge(session_table)

    def _sync_questions(self, session: Session, merged_session, db_session) -> None:
        """Synchronize questions between session and database."""
        existing_questions = {q.id: q for q in merged_session.questions}
        current_question_ids = set()

        for i, question in enumerate(session.questions):
            current_question_ids.add(question.id)
            if question.id in existing_questions:
                self._update_existing_question(
                    existing_questions[question.id], question, i
                )
            else:
                self._add_new_question(question, session.id, i, db_session)

        self._remove_orphaned_questions(
            existing_questions, current_question_ids, db_session
        )

    def _update_existing_question(self, existing_q, question, order_index: int) -> None:
        """Update existing question with new data."""
        existing_q.text = question.text
        existing_q.category = question.category
        existing_q.required = question.required
        existing_q.order_index = order_index

    def _add_new_question(
        self, question, session_id: str, order_index: int, db_session
    ) -> None:
        """Add new question to database."""
        q_table = QuestionTable(
            id=question.id,
            session_id=session_id,
            text=question.text,
            category=question.category,
            required=question.required,
            order_index=order_index,
        )
        db_session.add(q_table)

    def _remove_orphaned_questions(
        self, existing_questions: dict, current_ids: set, db_session
    ) -> None:
        """Remove questions that are no longer present in session."""
        for q_id, existing_q in existing_questions.items():
            if q_id not in current_ids:
                db_session.delete(existing_q)

    def _sync_answers(self, session: Session, merged_session, db_session) -> None:
        """Synchronize answers between session and database."""
        existing_answers = {a.question_id: a for a in merged_session.answers}
        current_answer_q_ids = set()

        for answer in session.answers:
            current_answer_q_ids.add(answer.question_id)
            if answer.question_id in existing_answers:
                self._update_existing_answer(
                    existing_answers[answer.question_id], answer
                )
            else:
                self._add_new_answer(answer, session.id, db_session)

        self._remove_orphaned_answers(
            existing_answers, current_answer_q_ids, db_session
        )

    def _update_existing_answer(self, existing_a, answer) -> None:
        """Update existing answer with new data."""
        existing_a.text = answer.text
        existing_a.is_vague = answer.is_vague
        existing_a.needs_followup = answer.needs_followup

    def _add_new_answer(self, answer, session_id: str, db_session) -> None:
        """Add new answer to database."""
        a_table = AnswerTable(
            session_id=session_id,
            question_id=answer.question_id,
            text=answer.text,
            is_vague=answer.is_vague,
            needs_followup=answer.needs_followup,
        )
        db_session.add(a_table)

    def _remove_orphaned_answers(
        self, existing_answers: dict, current_ids: set, db_session
    ) -> None:
        """Remove answers that are no longer present in session."""
        for q_id, existing_a in existing_answers.items():
            if q_id not in current_ids:
                db_session.delete(existing_a)

    def _sync_requirements(self, session: Session, merged_session, db_session) -> None:
        """Synchronize requirements between session and database."""
        existing_requirements = {r.id: r for r in merged_session.requirements}
        current_requirement_ids = set()

        for i, requirement in enumerate(session.requirements):
            current_requirement_ids.add(requirement.id)
            if requirement.id in existing_requirements:
                self._update_existing_requirement(
                    existing_requirements[requirement.id], requirement, i
                )
            else:
                self._add_new_requirement(requirement, session.id, i, db_session)

        self._remove_orphaned_requirements(
            existing_requirements, current_requirement_ids, db_session
        )

    def _update_existing_requirement(
        self, existing_r, requirement, order_index: int
    ) -> None:
        """Update existing requirement with new data."""
        existing_r.title = requirement.title
        existing_r.rationale = requirement.rationale
        existing_r.priority = requirement.priority
        existing_r.order_index = order_index

    def _add_new_requirement(
        self, requirement, session_id: str, order_index: int, db_session
    ) -> None:
        """Add new requirement to database."""
        r_table = RequirementTable(
            id=requirement.id,
            session_id=session_id,
            title=requirement.title,
            rationale=requirement.rationale,
            priority=requirement.priority,
            order_index=order_index,
        )
        db_session.add(r_table)

    def _remove_orphaned_requirements(
        self, existing_requirements: dict, current_ids: set, db_session
    ) -> None:
        """Remove requirements that are no longer present in session."""
        for r_id, existing_r in existing_requirements.items():
            if r_id not in current_ids:
                db_session.delete(existing_r)

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
                        self._update_session_metadata(session)
                        state_context_json = self._serialize_state_context(session)
                        merged_session = self._upsert_session_record(
                            session, db_session, state_context_json
                        )

                        self._sync_questions(session, merged_session, db_session)
                        self._sync_answers(session, merged_session, db_session)
                        self._sync_requirements(session, merged_session, db_session)

                        db_session.commit()
                        return session.id

                    except Exception as e:
                        db_session.rollback()
                        raise SessionSaveError(
                            f"Failed to save session {session.id}: {str(e)}"
                        ) from e

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
                    session_table = self._fetch_session_with_relations(
                        db_session, session_id
                    )
                    if not session_table:
                        return None
                    return self._build_session_from_table(session_table)
                except Exception as e:
                    raise SessionLoadError(
                        f"Failed to load session {session_id}: {str(e)}"
                    ) from e

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
                    raise SessionDeleteError(
                        f"Failed to delete session {session_id}: {str(e)}"
                    ) from e
