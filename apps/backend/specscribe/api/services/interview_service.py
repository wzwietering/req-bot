"""API service wrapping the conversational interview pipeline."""

from datetime import UTC, datetime

from pydantic import ValidationError

from specscribe.core.conversation_state import ConversationState
from specscribe.core.database_models import UserTable
from specscribe.core.logging import log_event
from specscribe.core.models import Answer, AnswerAnalysis, Question, Session
from specscribe.core.pipeline import ConversationalInterviewPipeline
from specscribe.core.services.exceptions import QuotaExceededError
from specscribe.core.services.usage_tracking_service import UsageTrackingService
from specscribe.core.state_manager import ConversationStateManager
from specscribe.core.storage import DatabaseManager
from specscribe.core.storage_interface import StorageInterface
from specscribe.providers.exceptions import OverloadedError


class APIInterviewService:
    """Wraps ConversationalInterviewPipeline for API use."""

    def __init__(self, storage: StorageInterface, model_id: str):
        self.storage = storage
        self.model_id = model_id
        # Usage tracking requires DatabaseManager for session access
        if isinstance(storage, DatabaseManager):
            self.usage_service = UsageTrackingService(storage)
        else:
            self.usage_service = None  # type: ignore

    def create_session(self, project: str, user_id: str) -> Session:
        """Create new session with LLM-generated questions."""
        pipeline = ConversationalInterviewPipeline(
            project=project, model_id=self.model_id, storage=self.storage, session_id=None
        )

        session, _ = pipeline.setup_session(session_id=None)
        session.user_id = user_id

        try:
            self.storage.save_session(session)

            # Track AI-generated questions (batch insert for performance)
            if self.usage_service and session.questions:
                question_ids = [q.id for q in session.questions]
                self.usage_service.record_questions_batch(user_id, question_ids)
        except Exception as e:
            # If tracking fails, delete the session to maintain consistency
            try:
                self.storage.delete_session(session.id)
            except Exception:
                pass  # Log but don't fail if cleanup fails
            raise e

        return session

    def process_answer(self, session_id: str, answer_text: str) -> tuple[Session, bool, str | None]:
        """Process answer using pipeline's intelligent logic.

        Returns:
            (session, quota_exceeded, quota_message)
        """
        session = self.storage.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        pipeline = self._create_pipeline(session)

        current_question = self._get_current_question(session)

        if not current_question:
            # No current question - assess and finalize
            finalized_session = self._assess_and_finalize(session, pipeline)
            return (finalized_session, False, None)

        self._prepare_session_for_answer(session, pipeline)
        analysis = self._record_and_analyze_answer(session, pipeline, current_question, answer_text)
        quota_exceeded, quota_message = self._handle_followups_or_next_question(
            session, pipeline, current_question, analysis
        )
        self.storage.save_session(session)
        self._check_and_finalize_if_complete(session, pipeline, current_question)

        return (session, quota_exceeded, quota_message)

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

        # Track answer submission with unique identifier (session_id + question_id + timestamp)
        if self.usage_service:
            answer_id = f"{session.id}_{question.id}_{datetime.now(UTC).timestamp()}"
            self.usage_service.record_answer_submitted(session.user_id, answer_id)

        return analysis

    def _check_quota_available(self, user_id: str) -> tuple[bool, str | None]:
        """Check if user has quota available for LLM operations.

        Returns:
            (has_quota, error_message) - if has_quota is False, error_message explains why
        """
        if not self.usage_service or not isinstance(self.storage, DatabaseManager):
            return (True, None)

        try:
            with self.storage.SessionLocal() as db_session:
                user = db_session.get(UserTable, user_id)
                if user:
                    self.usage_service.check_quota_available(user_id, user.tier)
            return (True, None)
        except QuotaExceededError as e:
            return (False, str(e))

    def _generate_and_track_followups(
        self,
        session: Session,
        pipeline: ConversationalInterviewPipeline,
        analysis: AnswerAnalysis,
        current_question: Question,
    ) -> tuple[bool, str | None]:
        """Generate and track followup questions.

        Returns:
            (quota_exceeded, quota_message)
        """
        has_quota, quota_msg = self._check_quota_available(session.user_id)
        if not has_quota:
            log_event("quota.exceeded.followups_skipped", user_id=session.user_id, quota_error=quota_msg)
            return (True, quota_msg)

        pipeline.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_FOLLOWUPS)
        followup_questions = pipeline.question_queue_manager.insert_followups(
            analysis.follow_up_questions, current_question, session
        )

        if self.usage_service:
            for followup in followup_questions:
                self.usage_service.record_question_generated(session.user_id, followup.id)

        return (False, None)

    def _generate_and_track_next_question(
        self, session: Session, pipeline: ConversationalInterviewPipeline
    ) -> tuple[bool, str | None]:
        """Generate and track next question.

        Returns:
            (quota_exceeded, quota_message)
        """
        has_quota, quota_msg = self._check_quota_available(session.user_id)
        if not has_quota:
            log_event("quota.exceeded.next_question_skipped", user_id=session.user_id, quota_error=quota_msg)
            return (True, quota_msg)

        next_question = pipeline.question_generation.generate_next_question_if_needed(session)
        if next_question:
            session.questions.append(next_question)
            if self.usage_service:
                self.usage_service.record_question_generated(session.user_id, next_question.id)

        return (False, None)

    def _handle_followups_or_next_question(
        self, session: Session, pipeline: ConversationalInterviewPipeline, current_question: Question, analysis
    ) -> tuple[bool, str | None]:
        """Handle follow-up questions or generate next question.

        Returns:
            (quota_exceeded, quota_message)
        """
        if analysis.follow_up_questions:
            return self._generate_and_track_followups(session, pipeline, analysis, current_question)
        else:
            return self._generate_and_track_next_question(session, pipeline)

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

    def _get_unanswered_question(self, session: Session) -> Question | None:
        """Find next unanswered question in session."""
        answered_ids = {a.question_id for a in session.answers}
        return next((q for q in session.questions if q.id not in answered_ids), None)

    def _force_session_completion(self, session: Session) -> Session:
        """Force session completion when no questions available and not marked complete."""
        log_event(
            "interview.forced_completion",
            session_id=session.id,
            reason="No question could be generated and completeness assessment did not mark session complete",
            answered_count=len(session.answers),
        )
        pipeline = self._create_pipeline(session)
        session.conversation_complete = True

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
        return session

    def get_next_question(self, session: Session) -> tuple[Question | None, Session, bool, str | None]:
        """Get next unanswered question with just-in-time generation.

        Returns:
            (next_question, updated_session, quota_exceeded, quota_message).
        """
        if session.conversation_complete:
            return (None, session, False, None)

        next_question = self._get_unanswered_question(session)

        if not next_question:
            next_question, quota_exceeded, quota_msg = self._try_generate_next_question(session)
            if quota_exceeded:
                return (next_question, session, quota_exceeded, quota_msg)

        if not next_question:
            pipeline = self._create_pipeline(session)
            session = self._assess_and_finalize(session, pipeline)

        # DEFENSIVE: Ensure session consistency
        if not next_question and not session.conversation_complete:
            session = self._force_session_completion(session)

        return (next_question, session, False, None)

    def _save_and_track_generated_question(self, session: Session, question: Question) -> None:
        """Save generated question to session and track usage."""
        existing_ids = {q.id for q in session.questions}
        if question.id in existing_ids:
            return  # Already exists, possible race condition

        session.questions.append(question)
        self.storage.save_session(session)

        if self.usage_service:
            self.usage_service.record_question_generated(session.user_id, question.id)

    def _try_generate_next_question(self, session: Session) -> tuple[Question | None, bool, str | None]:
        """Try to generate the next question using just-in-time generation.

        Returns:
            (question, quota_exceeded, quota_message)
        """
        has_quota, quota_msg = self._check_quota_available(session.user_id)
        if not has_quota:
            log_event(
                "quota.exceeded.generation_skipped",
                session_id=session.id,
                user_id=session.user_id,
                quota_error=quota_msg,
            )
            return (None, True, quota_msg)

        pipeline = self._create_pipeline(session)
        new_question = pipeline.question_generation.generate_next_question_if_needed(session)

        if new_question:
            self._save_and_track_generated_question(session, new_question)

        return (new_question, False, None)

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
        """Ensure session is in a valid state before processing answer."""
        current_state = session.conversation_state

        if current_state == ConversationState.WAITING_FOR_INPUT:
            return

        recoverable_states = [
            ConversationState.PROCESSING_ANSWER,
            ConversationState.ASSESSING_COMPLETENESS,
            ConversationState.GENERATING_FOLLOWUPS,
            ConversationState.INITIALIZING,
            ConversationState.GENERATING_QUESTIONS,
        ]

        if current_state in recoverable_states:
            state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
