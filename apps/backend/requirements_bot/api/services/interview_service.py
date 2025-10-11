"""API service wrapping the conversational interview pipeline."""

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.pipeline import ConversationalInterviewPipeline
from requirements_bot.core.storage_interface import StorageInterface


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
    ):
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

        question_queue = []
        pipeline.completeness_assessment.assess_and_handle_completeness(session, question_queue)

        if session.conversation_complete:
            session = pipeline.finalize_session(session)

        self.storage.save_session(session)
        return session

    def get_next_question(self, session: Session) -> Question | None:
        """Get next unanswered question with just-in-time generation.

        If no questions remain and none can be generated, triggers completeness
        assessment to determine if the interview should be finalized.
        """
        # If already complete, no more questions
        if session.conversation_complete:
            return None

        answered_ids = {a.question_id for a in session.answers}
        next_question = next((q for q in session.questions if q.id not in answered_ids), None)

        # If no questions in queue, try to generate next question
        if not next_question:
            next_question = self._try_generate_next_question(session)

        # If still no question available, assess completeness and potentially finalize
        if not next_question:
            pipeline = ConversationalInterviewPipeline(
                project=session.project, model_id=self.model_id, storage=self.storage, session_id=session.id
            )
            updated_session = self._assess_and_finalize(session, pipeline)
            # Copy updated attributes back to the session object reference
            session.conversation_complete = updated_session.conversation_complete
            session.requirements = updated_session.requirements
            session.conversation_state = updated_session.conversation_state
            session.updated_at = updated_session.updated_at

        return next_question

    def _try_generate_next_question(self, session: Session) -> Question | None:
        """Try to generate the next question using just-in-time generation."""
        pipeline = self._create_pipeline(session)

        new_question = pipeline.question_generation.generate_next_question_if_needed(session)
        if new_question:
            session.questions.append(new_question)
            self.storage.save_session(session)

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
        except Exception:
            # Ensure we save failed state on any error
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

    def _ensure_safe_state_for_processing(self, session: Session, state_manager) -> None:
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
