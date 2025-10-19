import logging
import uuid

from specscribe.core.conversation_state import ConversationState
from specscribe.core.interview.question_queue import REQUIREMENT_AREAS, QuestionQueue
from specscribe.core.logging import log_event, span
from specscribe.core.models import Question, Session
from specscribe.core.prompts import generate_single_question_prompt
from specscribe.core.session_manager import SessionManager
from specscribe.providers.base import Provider


class QuestionGenerationService:
    """Handles all question generation logic for interviews with just-in-time generation."""

    def __init__(
        self,
        provider: Provider,
        session_manager: SessionManager,
        question_queue_manager: QuestionQueue,
        model_id: str,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.question_queue_manager = question_queue_manager
        self.model_id = model_id

    def setup_initial_session_questions(self, session: Session, project: str) -> None:
        """Generate just the first question to start the interview."""
        self.session_manager.state_manager.create_checkpoint(session, "generate_initial_questions")

        # Start with the first area (scope)
        first_question = self._generate_single_question(project=project, target_area=REQUIREMENT_AREAS[0], context="")

        if first_question:
            session.questions = [first_question]
        else:
            # Fallback: create a basic scope question
            session.questions = [
                Question(
                    id=str(uuid.uuid4()),
                    text="What problem are you trying to solve with this project?",
                    category="scope",
                    required=True,
                )
            ]

        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

    def generate_next_question_if_needed(self, session: Session) -> Question | None:
        """Generate one question only if queue is low and areas need coverage."""
        if not self.question_queue_manager.should_generate_more(session):
            return None

        target_area = self.question_queue_manager.get_next_target_area(session)
        if not target_area:
            return None  # All areas covered

        context = self._get_recent_context(session, last_n=5)
        return self._generate_single_question(session.project, target_area, context)

    def _generate_single_question(self, project: str, target_area: str, context: str) -> Question | None:
        """Generate ONE question for a specific area with full context."""
        try:
            prompt = generate_single_question_prompt(project, target_area, context)

            with span(
                "llm.generate_single_question",
                component="pipeline",
                operation="generate_single_question",
                provider_model=self.model_id,
                target_area=target_area,
            ):
                question = self.provider.generate_single_question(prompt)
                return question

        except Exception as e:
            log_event(
                "llm.generate_single_question_failed",
                component="pipeline",
                operation="generate_single_question",
                provider_model=self.model_id,
                target_area=target_area,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            print(f"⚠ LLM question generation failed for {target_area}: {e}")
            return None

    def _get_recent_context(self, session: Session, last_n: int = 5) -> str:
        """Get recent Q&A pairs for context."""
        if not session.answers:
            return ""

        answer_map = {a.question_id: a.text for a in session.answers}
        qa_pairs = []

        # Get the last N answered questions
        answered_questions = [q for q in session.questions if q.id in answer_map][-last_n:]

        for q in answered_questions:
            answer_text = answer_map.get(q.id, "")
            qa_pairs.append(f"Q: {q.text}\nA: {answer_text}")

        return "\n\n".join(qa_pairs)
