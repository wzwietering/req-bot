"""Service for handling session answer processing and completion logic."""

from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.storage_interface import StorageInterface


class SessionAnswerService:
    """Handles answer processing and session completion logic."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def process_answer(self, session: Session, question: Question, answer_text: str) -> tuple[Session, bool]:
        """Process an answer and return updated session and completion status.

        Args:
            session: The session to update
            question: The question being answered
            answer_text: The answer text

        Returns:
            tuple: (updated_session, is_complete)
        """
        # Create answer object
        answer = Answer(question_id=question.id, text=answer_text)

        # Add answer to session
        session.answers.append(answer)

        # Check if conversation is complete using centralized logic
        is_complete = self._is_session_complete(session)
        session.conversation_complete = is_complete

        # Save session
        self.storage.save_session(session)

        return session, is_complete

    def _is_session_complete(self, session: Session) -> bool:
        """Determine if a session is complete based on answered questions.

        This centralizes the completion logic that was previously duplicated
        in the API layer.

        Args:
            session: The session to check

        Returns:
            bool: True if the session is complete
        """
        # For now, simple logic: all questions must be answered
        answered_question_ids = {answer.question_id for answer in session.answers}
        return all(question.id in answered_question_ids for question in session.questions)

    def get_next_unanswered_question(self, session: Session) -> Question | None:
        """Get the next unanswered question for a session.

        Args:
            session: The session to check

        Returns:
            Question | None: The next unanswered question, or None if all are answered
        """
        answered_question_ids = {answer.question_id for answer in session.answers}
        for question in session.questions:
            if question.id not in answered_question_ids:
                return question
        return None

    def get_session_progress(self, session: Session) -> dict[str, int | float]:
        """Get session progress statistics.

        Args:
            session: The session to analyze

        Returns:
            dict: Progress statistics
        """
        total_questions = len(session.questions)
        answered_questions = len(session.answers)
        remaining_questions = total_questions - answered_questions
        completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0.0

        return {
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "remaining_questions": remaining_questions,
            "completion_percentage": completion_percentage,
        }
