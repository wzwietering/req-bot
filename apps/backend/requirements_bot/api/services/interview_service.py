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

        pipeline = ConversationalInterviewPipeline(
            project=session.project, model_id=self.model_id, storage=self.storage, session_id=session.id
        )

        answered_ids = {a.question_id for a in session.answers}
        current_question = next((q for q in session.questions if q.id not in answered_ids), None)

        if not current_question:
            return self._assess_and_finalize(session, pipeline)

        pipeline.session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)

        answer = Answer(question_id=current_question.id, text=answer_text)
        session.answers.append(answer)
        pipeline.conductor.log_answer_received(session, current_question, answer_text)

        analysis = pipeline.conductor.analyze_response(current_question, answer, session, self.model_id)
        pipeline.conductor.update_answer_metadata(answer, analysis)

        if analysis.follow_up_questions:
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_FOLLOWUPS)
            pipeline.question_queue_manager.insert_followups(analysis.follow_up_questions, current_question, session)
        else:
            # Just-in-time generation: Check if we need to generate next question
            next_question = pipeline.question_generation.generate_next_question_if_needed(session)
            if next_question:
                session.questions.append(next_question)

        self.storage.save_session(session)

        question_count = len(session.answers)
        unanswered = [q for q in session.questions if q.id not in answered_ids and q.id != current_question.id]
        remaining_count = len(unanswered)

        if pipeline.completeness_assessment.should_check_completeness(question_count, remaining_count):
            question_queue = unanswered
            question_queue = pipeline.completeness_assessment.assess_and_handle_completeness(session, question_queue)

            if session.conversation_complete:
                session = pipeline.finalize_session(session)
                self.storage.save_session(session)
        else:
            pipeline.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

        return session

    def _assess_and_finalize(self, session: Session, pipeline: ConversationalInterviewPipeline) -> Session:
        """Assess completeness and finalize if ready."""
        # Need to be in PROCESSING_ANSWER state to transition to ASSESSING_COMPLETENESS
        pipeline.session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)

        question_queue = []
        pipeline.completeness_assessment.assess_and_handle_completeness(session, question_queue)

        if session.conversation_complete:
            session = pipeline.finalize_session(session)

        self.storage.save_session(session)
        return session

    def get_next_question(self, session: Session) -> Question | None:
        """Get next unanswered question."""
        answered_ids = {a.question_id for a in session.answers}
        return next((q for q in session.questions if q.id not in answered_ids), None)
