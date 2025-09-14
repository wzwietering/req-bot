from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.models import Session
from requirements_bot.core.session_manager import SessionManager


class SessionSetupManager:
    """Handles session setup logic for both new and existing sessions."""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def setup_session(
        self, project: str, session_id: str | None, mode: str
    ) -> tuple[Session, int]:
        """Set up session for interview, either loading existing or creating new.

        Returns:
            tuple[Session, int]: The session and the question counter (number of answered questions)
        """
        session = None
        if session_id:
            session = self.session_manager.load_existing_session(session_id, mode)

        if session:
            return session, len(session.answers)
        else:
            if session_id:
                print(f"\n⚠ Session {session_id} not found, starting new interview")
            return self._create_new_session(project, mode), 0

    def _create_new_session(self, project: str, mode: str) -> Session:
        """Create new session for specified mode."""
        session = self.session_manager.create_new_session(project, [], mode)
        return session
