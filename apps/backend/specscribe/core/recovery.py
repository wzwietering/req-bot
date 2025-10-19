import logging
import threading
import uuid

from specscribe.core.conversation_state import ConversationState
from specscribe.core.interview.question_queue import REQUIREMENT_AREAS
from specscribe.core.logging import log_event
from specscribe.core.models import Question, Session
from specscribe.core.prompts import generate_single_question_prompt


class StateRecoveryManager:
    """Handles recovery from interrupted conversation states."""

    def __init__(self, session_manager, question_queue_manager, provider):
        self.session_manager = session_manager
        self.question_queue_manager = question_queue_manager
        self.provider = provider
        self._recovery_locks: dict[str, threading.Lock] = {}
        self._lock_manager_lock = threading.Lock()

    def _get_recovery_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a specific session recovery to prevent race conditions."""
        with self._lock_manager_lock:
            if session_id not in self._recovery_locks:
                self._recovery_locks[session_id] = threading.Lock()
            return self._recovery_locks[session_id]

    def attempt_recovery(self, session: Session) -> bool:
        """Attempt to recover from the current conversation state."""
        recovery_lock = self._get_recovery_lock(session.id)

        with recovery_lock:
            state = session.conversation_state
            recovery_action = self.session_manager.state_manager.determine_recovery_action(session)

            log_event(
                "conversation.recovery_attempt",
                component="recovery",
                operation="attempt_recovery",
                session_id=session.id,
                from_state=state.value,
                recovery_action=recovery_action,
            )

            try:
                recovery_methods = {
                    "restart_initialization": self._restart_initialization,
                    "retry_question_generation": self._retry_question_generation,
                    "continue_from_question": self._continue_from_question,
                    "reprocess_last_answer": self._reprocess_last_answer,
                    "skip_followups_continue": self._skip_followups_continue,
                    "assume_incomplete_continue": self._assume_incomplete_continue,
                    "retry_requirements_generation": self._retry_requirements_generation,
                }

                recovery_method = recovery_methods.get(recovery_action, self._restart_from_beginning)
                return recovery_method(session)

            except Exception as e:
                log_event(
                    "conversation.recovery_failed",
                    component="recovery",
                    operation="recovery_failed",
                    session_id=session.id,
                    error=str(e),
                )
                return False

    def _restart_initialization(self, session: Session) -> bool:
        """Restart from initialization state."""
        self.session_manager.state_manager.transition_to(session, ConversationState.INITIALIZING)
        return True

    def _retry_question_generation(self, session: Session) -> bool:
        """Retry question generation from last checkpoint."""
        try:
            # If no questions exist, generate just one to get started
            if not session.questions:
                # Try to generate a single question
                prompt = generate_single_question_prompt(session.project, REQUIREMENT_AREAS[0], "")
                question = self.provider.generate_single_question(prompt)
                if question:
                    session.questions = [question]
                else:
                    # If LLM generation fails completely, try basic fallback
                    session.questions = [
                        Question(
                            id=str(uuid.uuid4()),
                            text="What problem are you trying to solve with this project?",
                            category="scope",
                            required=True,
                        )
                    ]

            self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
            return True
        except Exception:
            # If question generation fails, fall back to continuing with existing questions
            if session.questions:
                self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
                return True
            return False

    def _continue_from_question(self, session: Session) -> bool:
        """Continue from current question position."""
        # Simply transition to waiting for input state
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return True

    def _reprocess_last_answer(self, session: Session) -> bool:
        """Remove and reprocess the last answer."""
        if session.answers:
            # Remove last answer to reprocess
            last_answer = session.answers.pop()
            log_event(
                "conversation.reprocessing_answer",
                component="recovery",
                operation="reprocess_last_answer",
                session_id=session.id,
                answer_preview=last_answer.text[:50],
                level=logging.INFO,
            )

        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return True

    def _skip_followups_continue(self, session: Session) -> bool:
        """Skip follow-up generation and continue."""
        log_event(
            "conversation.skipping_followups",
            component="recovery",
            operation="skip_followups_continue",
            session_id=session.id,
            level=logging.INFO,
        )
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return True

    def _assume_incomplete_continue(self, session: Session) -> bool:
        """Assume interview is incomplete and continue."""
        log_event(
            "conversation.assuming_incomplete",
            component="recovery",
            operation="assume_incomplete_continue",
            session_id=session.id,
            level=logging.INFO,
        )
        session.conversation_complete = False
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return True

    def _retry_requirements_generation(self, session: Session) -> bool:
        """Retry requirements generation."""
        try:
            log_event(
                "conversation.retrying_requirements_generation",
                component="recovery",
                operation="retry_requirements_generation",
                session_id=session.id,
                level=logging.INFO,
            )
            self.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_REQUIREMENTS)
            return True
        except Exception:
            return False

    def _restart_from_beginning(self, session: Session) -> bool:
        """Fallback: restart from beginning."""
        log_event(
            "conversation.restarting_from_beginning",
            component="recovery",
            operation="restart_from_beginning",
            session_id=session.id,
            level=logging.WARNING,
        )
        session.answers.clear()
        session.requirements.clear()
        session.conversation_complete = False
        self.session_manager.state_manager.transition_to(session, ConversationState.INITIALIZING)
        return True
