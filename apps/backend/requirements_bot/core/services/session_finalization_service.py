from pydantic import ValidationError

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.interview.utils import generate_requirements
from requirements_bot.core.io_interface import IOInterface
from requirements_bot.core.logging import log_event
from requirements_bot.core.models import Session
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.providers.base import Provider
from requirements_bot.providers.exceptions import OverloadedError


class SessionFinalizationService:
    """Handles session finalization including requirements generation."""

    def __init__(
        self,
        provider: Provider,
        session_manager: SessionManager,
        model_id: str,
        project: str,
        io: IOInterface,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.model_id = model_id
        self.project = project
        self.io = io

    def finalize_session(self, session: Session) -> Session:
        """Generate requirements and finalize the session."""
        self.io.print_requirements_generation(len(session.answers))

        # Only transition if not already in GENERATING_REQUIREMENTS state (e.g., during retry)
        if session.conversation_state != ConversationState.GENERATING_REQUIREMENTS:
            self.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_REQUIREMENTS)

        self.session_manager.state_manager.create_checkpoint(session, "generate_final_requirements")

        try:
            requirements = generate_requirements(
                self.provider,
                self.project,
                session.questions,
                session.answers,
                session.id,
                self.model_id,
            )

            # Validate requirements were actually generated
            if not requirements:
                log_event(
                    "requirements.generation_empty",
                    component="finalization",
                    operation="finalize_session",
                    session_id=session.id,
                    answers_count=len(session.answers),
                )
                self.session_manager.state_manager.transition_to(session, ConversationState.FAILED)
                return session

            session.requirements = requirements
            self.session_manager.mark_session_complete(session)
            return session

        except (ValidationError, OverloadedError) as e:
            # Critical errors - don't mark session as complete
            log_event(
                "requirements.generation_failed",
                component="finalization",
                operation="finalize_session",
                session_id=session.id,
                error_type=type(e).__name__,
                error_msg=str(e),
            )
            self.session_manager.state_manager.transition_to(session, ConversationState.FAILED)
            return session
