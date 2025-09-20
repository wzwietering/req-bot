from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.interview.utils import (
    generate_requirements,
    print_requirements_generation,
)
from requirements_bot.core.models import Session
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.providers.base import Provider


class SessionFinalizationService:
    """Handles session finalization including requirements generation."""

    def __init__(
        self,
        provider: Provider,
        session_manager: SessionManager,
        model_id: str,
        project: str,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.model_id = model_id
        self.project = project

    def finalize_session(self, session: Session) -> Session:
        """Generate requirements and finalize the session."""
        print_requirements_generation(len(session.answers))
        self.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_REQUIREMENTS)
        self.session_manager.state_manager.create_checkpoint(session, "generate_final_requirements")

        requirements = generate_requirements(
            self.provider,
            self.project,
            session.questions,
            session.answers,
            session.id,
            self.model_id,
        )
        session.requirements = requirements
        self.session_manager.mark_session_complete(session)
        return session
