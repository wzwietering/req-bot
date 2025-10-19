import logging

from specscribe.core.conversation_state import ConversationState
from specscribe.core.interview.interview_conductor import InterviewConductor
from specscribe.core.logging import log_event
from specscribe.core.models import Session
from specscribe.core.services.question_generation_service import (
    QuestionGenerationService,
)
from specscribe.core.session_manager import SessionManager


class CompletenessAssessmentService:
    """Handles interview completeness assessment and related logic."""

    def __init__(
        self,
        conductor: InterviewConductor,
        session_manager: SessionManager,
        question_generation_service: QuestionGenerationService,
        model_id: str,
    ):
        self.conductor = conductor
        self.session_manager = session_manager
        self.question_generation_service = question_generation_service
        self.model_id = model_id

    def should_check_completeness(self, question_counter: int, queue_length: int) -> bool:
        """Determine if we should check interview completeness."""
        return self.conductor.should_check_completeness(question_counter, queue_length)

    def assess_and_handle_completeness(self, session: Session, question_queue: list) -> list:
        """Assess interview completeness and handle the result.

        Note: This method assumes we're currently in PROCESSING_ANSWER state,
        which allows transition to ASSESSING_COMPLETENESS.

        Returns:
            list: Updated question queue
        """

        self.session_manager.state_manager.transition_to(session, ConversationState.ASSESSING_COMPLETENESS)
        self.session_manager.state_manager.create_checkpoint(session, "assess_completeness")

        try:
            completeness = self.conductor.assess_interview_status(session, self.model_id)

            if completeness.is_complete:
                self.conductor.handle_completion(completeness)
                session.conversation_complete = True
            else:
                self.conductor.handle_missing_areas(completeness)
                # With just-in-time generation, the interview loop will generate
                # the next question when needed based on area coverage
                # Transition back to waiting for input to continue interview
                self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

        except Exception as e:
            # LLM call failed or assessment encountered an error
            # Recover gracefully by transitioning back to WAITING_FOR_INPUT
            log_event(
                "completeness_assessment.failed",
                component="completeness_assessment",
                operation="assess_and_handle",
                session_id=session.id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )

            # Always transition out of ASSESSING_COMPLETENESS to prevent stuck state
            self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

            # Re-raise if it's a critical error (not LLM/network related)
            # Allow interview to continue for transient errors
            if not isinstance(e, (TimeoutError, ConnectionError, Exception)):
                raise

        return question_queue
