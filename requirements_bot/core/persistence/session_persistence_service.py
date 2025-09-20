import json
from datetime import UTC, datetime

from requirements_bot.core.conversation_state import StateContext
from requirements_bot.core.database_models import SessionTable
from requirements_bot.core.logging import span
from requirements_bot.core.models import Session

from .answer_synchronizer import AnswerSynchronizer
from .question_synchronizer import QuestionSynchronizer
from .requirement_synchronizer import RequirementSynchronizer


class SessionPersistenceService:
    """Coordinates persistence operations for sessions and their related data."""

    def __init__(self):
        self.question_sync = QuestionSynchronizer()
        self.answer_sync = AnswerSynchronizer()
        self.requirement_sync = RequirementSynchronizer()

    def save_session_data(self, session: Session, db_session) -> str:
        """Save all session data using coordinated synchronizers."""
        with span(
            "db.save_session_data",
            component="persistence",
            operation="save_session_data",
            session_id=session.id,
        ):
            self._update_session_metadata(session)
            state_context_json = self._serialize_state_context(session)
            merged_session = self._upsert_session_record(session, db_session, state_context_json)

            self.question_sync.sync_questions(session, merged_session, db_session)
            self.answer_sync.sync_answers(session, merged_session, db_session)
            self.requirement_sync.sync_requirements(session, merged_session, db_session)

            return session.id

    def build_session_from_table(self, session_table) -> Session:
        """Build Session object from database table using specialized converters."""
        questions = self.question_sync.convert_questions_from_table(session_table)
        answers = self.answer_sync.convert_answers_from_table(session_table)
        requirements = self.requirement_sync.convert_requirements_from_table(session_table)
        state_context = self._deserialize_state_context(session_table.state_context)

        from requirements_bot.core.conversation_state import ConversationState

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
            last_state_change=session_table.last_state_change or session_table.updated_at,
        )

    def _update_session_metadata(self, session: Session) -> None:
        """Update session timestamps."""
        session.updated_at = datetime.now(UTC)

    def _serialize_state_context(self, session: Session) -> str:
        """Serialize state context to JSON."""
        return json.dumps(session.state_context.model_dump())

    def _upsert_session_record(self, session: Session, db_session, state_context_json: str):
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

    def _deserialize_state_context(self, context_json: str | None) -> StateContext:
        """Deserialize state context from JSON with fallback to default."""
        if not context_json:
            return StateContext()

        try:
            context_data = json.loads(context_json)
            return StateContext.model_validate(context_data)
        except (json.JSONDecodeError, ValueError):
            return StateContext()
