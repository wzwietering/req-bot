import logging
from datetime import UTC, datetime

from requirements_bot.core.conversation_state import (
    ConversationState,
    StateTransitionError,
    validate_context_for_state,
    validate_transition,
)
from requirements_bot.core.logging import log_event, span
from requirements_bot.core.models import Session
from requirements_bot.core.storage_interface import StorageInterface


class ConversationStateManager:
    """Manages conversation state transitions and recovery."""

    def __init__(self, storage: StorageInterface | None = None):
        self.storage = storage

    def transition_to(
        self,
        session: Session,
        new_state: ConversationState,
        context_updates: dict | None = None,
    ) -> None:
        """Safely transition to a new state with validation."""
        if not isinstance(session, Session):
            raise ValueError(f"Invalid session type: {type(session)}")
        if not isinstance(new_state, ConversationState):
            raise ValueError(f"Invalid new_state type: {type(new_state)}")
        if context_updates is not None and not isinstance(context_updates, dict):
            raise ValueError(f"context_updates must be dict or None, got: {type(context_updates)}")

        current_state = session.conversation_state

        if not validate_transition(current_state, new_state):
            raise StateTransitionError(f"Invalid transition from {current_state.value} to {new_state.value}")

        # Update state context if provided
        if context_updates:
            for key, value in context_updates.items():
                if hasattr(session.state_context, key):
                    setattr(session.state_context, key, value)

            # Validate context is appropriate for target state
            validation_issues = validate_context_for_state(new_state, session.state_context)
            if validation_issues:
                log_event(
                    "conversation.context_validation_warning",
                    component="state_manager",
                    operation="transition",
                    session_id=session.id,
                    to_state=new_state.value,
                    issues=validation_issues,
                )

        # Update session state
        session.conversation_state = new_state
        session.last_state_change = datetime.now(UTC)

        # Log the transition
        log_event(
            "conversation.state_transition",
            component="state_manager",
            operation="transition",
            session_id=session.id,
            from_state=current_state.value,
            to_state=new_state.value,
        )

        # Persist if storage available
        if self.storage:
            self._save_with_retry(session, new_state)

    def create_checkpoint(self, session: Session, operation_id: str) -> None:
        """Create a recovery checkpoint before risky operations."""
        if not isinstance(session, Session):
            raise ValueError(f"Invalid session type: {type(session)}")
        if not isinstance(operation_id, str):
            raise ValueError(f"operation_id must be string, got: {type(operation_id)}")
        if not operation_id.strip():
            raise ValueError("operation_id cannot be empty")

        session.state_context.llm_operation_id = operation_id

        if self.storage:
            try:
                self.storage.save_session(session)
            except Exception as e:
                log_event(
                    "conversation.checkpoint_creation_failed",
                    component="state_manager",
                    operation="create_checkpoint",
                    session_id=session.id,
                    operation_id=operation_id,
                    error=str(e),
                    level=logging.WARNING,
                )

    def can_recover_from_interruption(self, session: Session) -> bool:
        """Check if session can be recovered from its current state."""
        return session.conversation_state not in {
            ConversationState.COMPLETED,
            ConversationState.FAILED,
        }

    def determine_recovery_action(self, session: Session) -> str:
        """Determine what action to take for recovery based on current state."""
        state = session.conversation_state

        recovery_actions = {
            ConversationState.INITIALIZING: "restart_initialization",
            ConversationState.GENERATING_QUESTIONS: "retry_question_generation",
            ConversationState.WAITING_FOR_INPUT: "continue_from_question",
            ConversationState.PROCESSING_ANSWER: "reprocess_last_answer",
            ConversationState.GENERATING_FOLLOWUPS: "skip_followups_continue",
            ConversationState.ASSESSING_COMPLETENESS: "assume_incomplete_continue",
            ConversationState.GENERATING_REQUIREMENTS: "retry_requirements_generation",
        }

        return recovery_actions.get(state, "restart_from_beginning")

    def _save_with_retry(self, session: Session, state: ConversationState, max_retries: int = 3) -> None:
        """Save session state with retry logic for better reliability."""
        import time

        for attempt in range(max_retries):
            try:
                with span(
                    "db.save_state",
                    component="state_manager",
                    operation="save_state",
                    session_id=session.id,
                    state=state.value,
                    attempt=attempt + 1,
                ):
                    self.storage.save_session(session)
                return  # Success, exit early
            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 0.1 * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed, log the error
                    log_event(
                        "conversation.state_save_failed",
                        component="state_manager",
                        operation="save_state",
                        session_id=session.id,
                        error=str(e),
                        error_type=type(e).__name__,
                        attempts=max_retries,
                        level=logging.WARNING,
                    )
