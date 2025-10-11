import logging
import random
import time

from requirements_bot.core.constants import CLI_USER_ID
from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.logging import (
    get_run_id,
    get_trace_id,
    log_event,
    set_run_id,
    set_trace_id,
    span,
)
from requirements_bot.core.models import Question, Session
from requirements_bot.core.state_manager import ConversationStateManager
from requirements_bot.core.storage_interface import StorageInterface


class SessionManager:
    def __init__(self, storage: StorageInterface | None = None):
        self.storage = storage
        self.state_manager = ConversationStateManager(storage)

    def setup_logging_context(self) -> None:
        if not get_trace_id():
            rid = get_run_id()
            if not rid:
                rid = f"run-{random.randint(100000, 999999)}"
                set_run_id(rid)
            set_trace_id(rid)

    def load_existing_session(self, session_id: str) -> Session | None:
        if not self.storage:
            return None

        session = self.storage.load_session(session_id)
        if session:
            print(f"\n=== Resuming interview for '{session.project}' ===")
            print(f"   → Current state: {session.conversation_state.value}")

            # Check if recovery is needed
            if self.state_manager.can_recover_from_interruption(session):
                recovery_action = self.state_manager.determine_recovery_action(session)
                print(f"   → Recovery strategy: {recovery_action}")

            set_trace_id(session.id)
            log_event(
                "interview.resume",
                component="pipeline",
                operation="resume",
                session_id=session.id,
                project=session.project,
                conversation_state=session.conversation_state.value,
            )
        return session

    def create_new_session(self, project: str, questions: list[Question], user_id: str = CLI_USER_ID) -> Session:
        session = Session(
            project=project,
            user_id=user_id,
            questions=questions,
            answers=[],
            requirements=[],
            conversation_complete=False,
        )

        # Transition to generating questions state
        self.state_manager.transition_to(session, ConversationState.GENERATING_QUESTIONS)

        set_trace_id(session.id)
        log_event(
            "interview.start",
            component="pipeline",
            operation="start",
            session_id=session.id,
            project=project,
        )
        return session

    def save_with_error_handling(self, session: Session, is_final: bool = False) -> None:
        if not self.storage:
            return

        self._save_with_retry(session, is_final)

    def _save_with_retry(self, session: Session, is_final: bool, max_retries: int = 3) -> None:
        """Save session with retry logic for better reliability."""
        for attempt in range(max_retries):
            try:
                with span(
                    "db.save_session",
                    component="db",
                    operation="save_session",
                    session_id=session.id,
                    answers=len(session.answers),
                    questions=len(session.questions),
                    final=is_final,
                    attempt=attempt + 1,
                ):
                    self.storage.save_session(session)  # type: ignore[union-attr]
                return  # Success, exit early
            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 0.1 * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed, log the error
                    warning_type = "final session" if is_final else "session"
                    log_event(
                        "session.save_failed",
                        component="session_manager",
                        operation="save_session",
                        session_id=session.id,
                        session_type=warning_type,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempts=max_retries,
                        level=logging.WARNING,
                    )

    def mark_session_complete(self, session: Session) -> None:
        session.conversation_complete = True
        self.state_manager.transition_to(session, ConversationState.COMPLETED)
        self.save_with_error_handling(session, is_final=True)
