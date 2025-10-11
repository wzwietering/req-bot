"""API service wrapping the conversational interview pipeline."""

from pydantic import ValidationError

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.logging import log_event
from requirements_bot.core.models import Answer, AnswerAnalysis, Question, Session
from requirements_bot.core.pipeline import ConversationalInterviewPipeline
from requirements_bot.core.state_manager import ConversationStateManager
from requirements_bot.core.storage_interface import StorageInterface
from requirements_bot.providers.exceptions import OverloadedError


class APIInterviewService:
    """Wraps ConversationalInterviewPipeline for API use."""

    def __init__(self, storage: StorageInterface, model_id: str):
        self.storage = storage
        self.model_id = model_id

    def create_session(self, project: str, user_id: str) -> Session:
        """Create new session with LLM-generated questions."""
        pipeline = ConversationalInterviewPipeline(
            project=project, model_id=self.model_id, storage=self.storage, session_id=None
        )

        session, _ = pipeline.setup_session(session_id=None)

        session.user_id = user_id
        self.storage.save_session(session)

        return session

    def process_answer(self, session_id: str, answer_text: str) -> Session:
        """Process answer using pipeline's intelligent logic."""
        session = self.storage.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        pipeline = self._create_pipeline(session)

        current_question = self._get_current_question(session)

        if not current_question:
            return self._assess_and_finalize(session, pipeline)

        self._prepare_session_for_answer(session, pipeline)
        analysis = self._record_and_analyze_answer(session, pipeline, current_question, answer_text)
        self._handle_followups_or_next_question(session, pipeline, current_question, analysis)
        self.storage.save_session(session)
        self._check_and_finalize_if_complete(session, pipeline, current_question)

        return session

    def _create_pipeline(self, session: Session) -> ConversationalInterviewPipeline:
        """Create pipeline for session."""
        return ConversationalInterviewPipeline(
            project=session.project, model_id=self.model_id, storage=self.storage, session_id=session.id
        )

    def _get_current_question(self, session: Session) -> Question | None:
        """Get the current unanswered question."""
        answered_ids = {a.question_id for a in session.answers}
        return next((q for q in session.questions if q.id not in answered_ids), None)

    def _prepare_session_for_answer(self, session: Session, pipeline: ConversationalInterviewPipeline) -> None:
        """Prepare session state for answer processing."""
        self._ensure_safe_state_for_processing(session, pipeline.session_manager.state_manager)
        pipeline.session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)

    def _record_and_analyze_answer(
        self, session: Session, pipeline: ConversationalInterviewPipeline, question: Question, answer_text: str
    ) -> AnswerAnalysis:
        """Record and analyze the answer. Returns the analysis result."""
        answer = Answer(question_id=question.id, text=answer_text)
        session.answers.append(answer)
        pipeline.conductor.log_answer_received(session, question, answer_text)

        analysis = pipeline.conductor.analyze_response(question, answer, session, self.model_id)
        pipeline.conductor.update_answer_metadata(answer, analysis)
        return analysis

    def _handle_followups_or_next_question(
        self, session: Session, pipeline: ConversationalInterviewPipeline, current_question: Question, analysis
    ) -> None:
        """Handle follow-up questions or generate next question."""
        if analysis.follow_up_questions:
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_FOLLOWUPS)
            pipeline.question_queue_manager.insert_followups(analysis.follow_up_questions, current_question, session)
        else:
            next_question = pipeline.question_generation.generate_next_question_if_needed(session)
            if next_question:
                session.questions.append(next_question)

    def _check_and_finalize_if_complete(
        self, session: Session, pipeline: ConversationalInterviewPipeline, current_question: Question
    ) -> None:
        """Check completeness and finalize if ready."""
        answered_ids = {a.question_id for a in session.answers}
        unanswered = [q for q in session.questions if q.id not in answered_ids and q.id != current_question.id]

        question_count = len(session.answers)
        remaining_count = len(unanswered)

        if pipeline.completeness_assessment.should_check_completeness(question_count, remaining_count):
            pipeline.completeness_assessment.assess_and_handle_completeness(session, unanswered)

            if session.conversation_complete:
                session = pipeline.finalize_session(session)
                self.storage.save_session(session)
        else:
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

    def _assess_and_finalize(self, session: Session, pipeline: ConversationalInterviewPipeline) -> Session:
        """Assess completeness and finalize if ready."""
        # Handle state recovery - ensure we're in a valid state before processing
        self._ensure_safe_state_for_processing(session, pipeline.session_manager.state_manager)

        # Need to be in PROCESSING_ANSWER state to transition to ASSESSING_COMPLETENESS
        pipeline.session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)

        question_queue: list[Question] = []
        pipeline.completeness_assessment.assess_and_handle_completeness(session, question_queue)

        if session.conversation_complete:
            session = pipeline.finalize_session(session)

        self.storage.save_session(session)
        return session

    def get_next_question(self, session: Session) -> tuple[Question | None, Session]:
        """Get next unanswered question with just-in-time generation.

        If no questions remain and none can be generated, triggers completeness
        assessment to determine if the interview should be finalized.

        Returns:
            Tuple of (next_question, updated_session). The updated_session should
            be used by the caller as it may have been modified during finalization.
        """
        # If already complete, no more questions
        if session.conversation_complete:
            return None, session

        answered_ids = {a.question_id for a in session.answers}
        next_question = next((q for q in session.questions if q.id not in answered_ids), None)

        # If no questions in queue, try to generate next question
        if not next_question:
            next_question = self._try_generate_next_question(session)

        # If still no question available, assess completeness and potentially finalize
        if not next_question:
            pipeline = self._create_pipeline(session)
            session = self._assess_and_finalize(session, pipeline)

        # DEFENSIVE: Ensure invariant holds - if not complete, must have a question
        # This handles the edge case where both question generation AND completeness
        # assessment fail (e.g., LLM unavailable). Better to mark as complete than
        # return an invalid state.
        if not next_question and not session.conversation_complete:
            log_event(
                "interview.forced_completion",
                session_id=session.id,
                reason="No question could be generated and completeness assessment did not mark session complete",
                answered_count=len(session.answers),
            )
            pipeline = self._create_pipeline(session)
            session.conversation_complete = True
            # Try to finalize, but don't fail if it doesn't work
            try:
                session = pipeline.finalize_session(session)
            except Exception as e:
                log_event(
                    "interview.forced_completion_finalization_failed",
                    session_id=session.id,
                    error_type=type(e).__name__,
                    error=str(e),
                )
            self.storage.save_session(session)

        return next_question, session

    def _try_generate_next_question(self, session: Session) -> Question | None:
        """Try to generate the next question using just-in-time generation.

        Note: This method mutates the session by appending the new question.
        The session is saved immediately after generation to persist the change.
        Concurrent calls to this method on the same session may result in
        duplicate questions if the storage layer doesn't handle conflicts.
        """
        pipeline = self._create_pipeline(session)

        new_question = pipeline.question_generation.generate_next_question_if_needed(session)
        if new_question:
            # Check if question already exists before appending (defensive programming)
            existing_ids = {q.id for q in session.questions}
            if new_question.id not in existing_ids:
                session.questions.append(new_question)
                self.storage.save_session(session)
            else:
                # Question was already added (possible race condition)
                return new_question

        return new_question

    def retry_finalization(self, session: Session) -> Session:
        """Retry requirements generation for a failed/incomplete session."""
        if not self._can_retry_session(session):
            return session

        pipeline = ConversationalInterviewPipeline(
            project=session.project, model_id=self.model_id, storage=self.storage, session_id=session.id
        )

        try:
            self._reset_session_for_retry(session, pipeline)
            session = pipeline.finalize_session(session)
            self.storage.save_session(session)
            return session
        except (ValidationError, OverloadedError, ValueError, KeyError, TypeError):
            # Handle expected errors during finalization
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.FAILED)
            self.storage.save_session(session)
            raise
        except Exception as e:
            # Unexpected errors - log and mark as failed
            log_event(
                "interview.retry_unexpected_error",
                session_id=session.id,
                error_type=type(e).__name__,
                error=str(e),
            )
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.FAILED)
            self.storage.save_session(session)
            raise

    def _can_retry_session(self, session: Session) -> bool:
        """Check if session can be retried."""
        return (
            session.conversation_state == ConversationState.FAILED
            or (session.conversation_state == ConversationState.COMPLETED and len(session.requirements) == 0)
            or session.conversation_state == ConversationState.GENERATING_REQUIREMENTS
        )

    def _reset_session_for_retry(self, session: Session, pipeline: ConversationalInterviewPipeline) -> None:
        """Reset session state for retry - atomic operation."""
        if session.conversation_state != ConversationState.GENERATING_REQUIREMENTS:
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_REQUIREMENTS)
        session.conversation_complete = False

    def _ensure_safe_state_for_processing(self, session: Session, state_manager: ConversationStateManager) -> None:
        """Ensure session is in a valid state before processing answer.

        Handles recovery from stuck or invalid states by transitioning through
        valid intermediate states.
        """
        current_state = session.conversation_state

        # If already in a valid state for processing, do nothing
        if current_state == ConversationState.WAITING_FOR_INPUT:
            return

        # Handle stuck states that need recovery
        if current_state == ConversationState.ASSESSING_COMPLETENESS:
            # Session was stuck in assessment - recover by transitioning to WAITING_FOR_INPUT
            state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        elif current_state == ConversationState.GENERATING_FOLLOWUPS:
            # Follow-ups generation was interrupted - transition to WAITING_FOR_INPUT
            state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        elif current_state in [ConversationState.INITIALIZING, ConversationState.GENERATING_QUESTIONS]:
            # Session not ready for answers yet - transition to WAITING_FOR_INPUT
            state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        # PROCESSING_ANSWER, GENERATING_REQUIREMENTS, COMPLETED, FAILED states
        # will be handled by normal validation in state_manager.transition_to()
