import logging

from requirements_bot.core.constants import (
    MAX_ADDITIONAL_QUESTIONS,
    MAX_INITIAL_QUESTIONS,
    MAX_MISSING_AREA_QUESTIONS,
)
from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.interview.question_queue import QuestionQueue
from requirements_bot.core.logging import log_event, span
from requirements_bot.core.models import Session
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.providers.base import Provider


class QuestionGenerationService:
    """Handles all question generation logic for interviews."""

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
        """Generate and add initial questions to a new session."""
        self.session_manager.state_manager.create_checkpoint(session, "generate_initial_questions")

        seed_questions = self.question_queue_manager.initialize_from_seeds(shuffled=True)

        llm_questions = self._generate_questions_with_fallback(project, seed_questions, "generate_questions")

        session.questions = seed_questions + llm_questions[:MAX_INITIAL_QUESTIONS]
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

    def generate_additional_questions(self, session: Session) -> list:
        """Generate additional questions when queue is empty."""
        print("   → Generating new questions to continue the conversation")
        self.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_QUESTIONS)
        self.session_manager.state_manager.create_checkpoint(session, "generate_additional_questions")

        seed_questions = self.question_queue_manager.initialize_from_seeds(shuffled=False)

        additional_questions = self._generate_questions_with_fallback(
            session.project, seed_questions, "generate_additional_questions"
        )

        new_questions = self.question_queue_manager.filter_asked_questions(additional_questions, session)
        question_queue = new_questions[:MAX_ADDITIONAL_QUESTIONS]

        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return question_queue

    def generate_missing_area_questions(self, session: Session) -> list:
        """Generate questions for missing areas identified during completeness assessment."""
        print("   → Generating additional questions for missing areas")
        self.session_manager.state_manager.create_checkpoint(session, "generate_missing_area_questions")

        seed_questions = self.question_queue_manager.initialize_from_seeds(shuffled=False)

        additional_questions = self._generate_questions_with_fallback(
            session.project, seed_questions, "generate_missing_area_questions"
        )

        new_questions = self.question_queue_manager.filter_asked_questions(additional_questions, session)
        return new_questions[:MAX_MISSING_AREA_QUESTIONS]

    def _generate_questions_with_fallback(self, project: str, seed_questions: list, operation: str) -> list:
        """Generate questions with proper error handling and fallback."""
        try:
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=self.model_id,
                seed_count=len(seed_questions),
            ):
                return self.provider.generate_questions(project, seed_questions=seed_questions)
        except Exception as e:
            log_event(
                "llm.generate_questions_failed",
                component="pipeline",
                operation=operation,
                provider_model=self.model_id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            print(f"⚠ LLM question generation failed: {e}")

            if operation == "generate_questions":
                print("⚠ Continuing with seed questions only")
            else:
                print(f"⚠ Unable to generate questions for {operation}")

            return []
