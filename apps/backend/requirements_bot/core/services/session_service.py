import uuid

from requirements_bot.core.constants import CLI_USER_ID
from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.document import write_document
from requirements_bot.core.io_interface import IOInterface
from requirements_bot.core.models import Question, Session
from requirements_bot.core.services.question_service import QuestionService
from requirements_bot.core.services.session_answer_service import SessionAnswerService
from requirements_bot.core.services.session_setup_manager import SessionSetupManager
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.core.storage_interface import StorageInterface


class SessionValidationError(Exception):
    """Raised when session validation fails."""

    pass


class SessionService:
    """Unified service for session management across API and CLI."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage
        self.answer_service = SessionAnswerService(storage)
        session_manager = SessionManager(storage)
        self.setup_manager = SessionSetupManager(session_manager)

    def validate_session_id(self, session_id: str) -> str:
        """Validate session ID format and return cleaned ID.

        Args:
            session_id: The session ID to validate

        Returns:
            str: The validated session ID

        Raises:
            SessionValidationError: If session ID format is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise SessionValidationError(f"Invalid session ID: {session_id}")

        # Remove whitespace
        session_id = session_id.strip()

        # Validate as proper UUID
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise SessionValidationError(f"Invalid UUID format: {session_id}")

        return session_id

    def get_or_create_session(self, project: str, user_id: str, session_id: str | None = None) -> Session:
        """Get existing session or create new one with basic setup.

        Args:
            project: Project name for the session
            user_id: ID of the user creating/accessing the session
            session_id: Optional existing session ID

        Returns:
            Session: The session object

        Raises:
            SessionValidationError: If session_id is invalid or session not found
        """
        if session_id:
            validated_id = self.validate_session_id(session_id)
            session = self.storage.load_session(validated_id)
            if not session:
                raise SessionValidationError(f"Session {validated_id} not found")
            # Verify user owns this session
            if session.user_id != user_id:
                raise SessionValidationError(f"Access denied: Session {validated_id} not found")
            return session

        # Create new session
        session, _ = self.setup_manager.setup_session(project, None, user_id)

        # Add basic questions for new sessions
        if not session.questions:
            session.questions = QuestionService.generate_basic_questions(project)
            session.conversation_state = ConversationState.WAITING_FOR_INPUT

        self.storage.save_session(session)
        return session

    def process_answer_and_advance(self, session_id: str, answer_text: str, io: IOInterface) -> tuple[Session, bool]:
        """Process answer and advance session state.

        This consolidates the core business logic that was duplicated between
        API and CLI layers.

        Args:
            session_id: ID of the session
            answer_text: The user's answer text
            io: IO interface for user interaction

        Returns:
            tuple: (updated_session, is_complete)

        Raises:
            SessionValidationError: If session is invalid or not found
        """
        session = self._load_and_validate_session(session_id)

        if session.conversation_complete:
            return session, True

        return self._process_active_session_answer(session, answer_text)

    def _load_and_validate_session(self, session_id: str) -> Session:
        """Load and validate session exists.

        Args:
            session_id: ID of the session to load

        Returns:
            Session: The loaded session

        Raises:
            SessionValidationError: If session is invalid or not found
        """
        validated_id = self.validate_session_id(session_id)
        session = self.storage.load_session(validated_id)

        if not session:
            raise SessionValidationError(f"Session {validated_id} not found")

        return session

    def _process_active_session_answer(self, session: Session, answer_text: str) -> tuple[Session, bool]:
        """Process answer for an active session.

        Args:
            session: The active session
            answer_text: The user's answer text

        Returns:
            tuple: (updated_session, is_complete)
        """
        current_question = self._get_current_question_or_complete(session)
        if not current_question:
            return session, True

        return self.answer_service.process_answer(session, current_question, answer_text)

    def _get_current_question_or_complete(self, session: Session) -> Question | None:
        """Get current question or mark session complete if none available.

        Args:
            session: The session to check

        Returns:
            Question object or None if session should be completed
        """
        current_question = self.answer_service.get_next_unanswered_question(session)
        if not current_question:
            session.conversation_complete = True
            self.storage.save_session(session)

        return current_question

    def get_session_progress(self, session: Session) -> dict[str, int | float]:
        """Calculate session progress metrics.

        Args:
            session: The session to analyze

        Returns:
            dict: Progress metrics with keys: total_questions, answered_questions,
                 remaining_questions, completion_percentage
        """
        return self.answer_service.get_session_progress(session)

    def get_next_question(self, session: Session) -> str | None:
        """Get the next unanswered question for a session.

        Args:
            session: The session to check

        Returns:
            Optional[str]: The next question text, or None if complete
        """
        if session.conversation_complete:
            return None

        question = self.answer_service.get_next_unanswered_question(session)
        return question.text if question else None

    def setup_project_and_session(
        self, project: str | None, session_id: str | None, io: IOInterface
    ) -> tuple[str, Session]:
        """Set up project name and session for interview.

        This consolidates the project/session setup logic used by CLI.

        Args:
            project: Optional project name
            session_id: Optional session ID to resume
            io: IO interface for user interaction

        Returns:
            tuple: (project_name, session)

        Raises:
            SessionValidationError: If session_id is invalid or not found
        """
        # If resuming a session, get project from the session
        if session_id and not project:
            validated_id = self.validate_session_id(session_id)
            existing_session = self.storage.load_session(validated_id)
            if not existing_session:
                raise SessionValidationError(f"Session {validated_id} not found")
            project = existing_session.project
            return project, existing_session

        # If no project provided and not resuming, prompt for it
        if not project:
            project = io.input("Project name/title: ")

        # Get or create session
        session = self.get_or_create_session(project, CLI_USER_ID, session_id)
        return project, session

    def load_session_with_validation(self, session_id: str, user_id: str | None = None) -> Session:
        """Load session with validation, raising appropriate errors.

        Args:
            session_id: ID of the session to load
            user_id: Optional user ID to verify ownership

        Returns:
            Session: The loaded session

        Raises:
            SessionValidationError: If session_id is invalid or session not found
        """
        validated_id = self.validate_session_id(session_id)
        session = self.storage.load_session(validated_id)
        if not session:
            raise SessionValidationError(f"Session {validated_id} not found")

        # Verify user owns this session if user_id provided
        if user_id and session.user_id != user_id:
            raise SessionValidationError(f"Session {validated_id} not found")

        return session

    def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        """Delete a session with validation.

        Args:
            session_id: ID of the session to delete
            user_id: Optional user ID to verify ownership

        Raises:
            SessionValidationError: If session_id is invalid or access denied
        """
        # Load session first to verify ownership
        if user_id:
            self.load_session_with_validation(session_id, user_id)
        else:
            self.validate_session_id(session_id)

        self.storage.delete_session(session_id)

    def get_session_summaries(self, user_id: str | None = None) -> list[dict]:
        """Get summaries of sessions, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter sessions

        Returns:
            list[dict]: List of session summary data
        """
        if user_id:
            return self.storage.get_session_summaries_for_user(user_id)  # type: ignore[attr-defined]
        return self.storage.get_session_summaries()  # type: ignore[attr-defined]

    def finalize_session_with_document(self, session: Session, output_path: str, io: IOInterface) -> str:
        """Finalize session and write document with consistent messaging.

        Args:
            session: The session to finalize
            output_path: Path to write the document
            io: IO interface for messaging

        Returns:
            str: Path where the document was written
        """
        path = write_document(session, path=output_path)
        io.print_success(f"Requirements written to {path}")
        io.print_info(f"Session saved as {session.id}")
        return path

    def handle_session_error(self, error: Exception, io: IOInterface, exit_on_error: bool = False) -> None:
        """Handle session errors with consistent messaging.

        Args:
            error: The error that occurred
            io: IO interface for messaging
            exit_on_error: Whether to exit the application on error
        """
        if isinstance(error, SessionValidationError):
            io.print_error(f"Session error: {error}")
        else:
            io.print_error(f"Unexpected error: {error}")

        if exit_on_error:
            # For CLI usage - this could trigger an exit
            raise error
