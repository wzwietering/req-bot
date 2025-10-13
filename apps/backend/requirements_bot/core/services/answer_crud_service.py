"""CRUD service for Answer management."""

from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.services.exceptions import AnswerNotFoundError, SessionCompleteError
from requirements_bot.core.storage import StorageInterface


class AnswerCRUDService:
    """Service for answer CRUD operations."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def get_answer_by_question_id(self, session: Session, question_id: str) -> Answer | None:
        """Get an answer by its associated question ID.

        Args:
            session: The session object
            question_id: ID of the question

        Returns:
            Answer object if found, None otherwise
        """
        for answer in session.answers:
            if answer.question_id == question_id:
                return answer
        return None

    def list_answers(self, session: Session) -> list[Answer]:
        """List all answers for a session.

        Args:
            session: The session object

        Returns:
            List of Answer objects
        """
        return session.answers

    def update_answer(self, session: Session, question_id: str, text: str) -> tuple[Session, Answer]:
        """Update an existing answer.

        Args:
            session: The session object
            question_id: ID of the question whose answer to update
            text: New answer text

        Returns:
            Tuple of (updated session, updated answer)

        Raises:
            SessionCompleteError: If session is complete
            AnswerNotFoundError: If answer not found
        """
        if session.conversation_complete:
            raise SessionCompleteError("update answer")

        # Find the answer
        answer_index = None
        for i, answer in enumerate(session.answers):
            if answer.question_id == question_id:
                answer_index = i
                break

        if answer_index is None:
            raise AnswerNotFoundError(question_id)

        # Update the answer
        old_answer = session.answers[answer_index]
        updated_answer = Answer(
            question_id=question_id,
            text=text,
            is_vague=old_answer.is_vague,
            needs_followup=old_answer.needs_followup,
        )
        session.answers[answer_index] = updated_answer

        # Save session
        self.storage.save_session(session)

        return session, updated_answer

    def delete_answer(self, session: Session, question_id: str) -> Session:
        """Delete an answer from a session.

        This marks the question as unanswered and may affect session completion status.

        Args:
            session: The session object
            question_id: ID of the question whose answer to delete

        Returns:
            Updated session

        Raises:
            SessionCompleteError: If session is complete
            AnswerNotFoundError: If answer not found
        """
        if session.conversation_complete:
            raise SessionCompleteError("delete answer")

        # Find the answer
        answer = self.get_answer_by_question_id(session, question_id)
        if not answer:
            raise AnswerNotFoundError(question_id)

        # Remove answer from list
        session.answers = [a for a in session.answers if a.question_id != question_id]

        # Mark session as incomplete if it was complete
        if session.conversation_complete:
            session.conversation_complete = False

        # Save session
        self.storage.save_session(session)

        return session

    def get_question_for_answer(self, session: Session, question_id: str) -> Question | None:
        """Get the question associated with an answer.

        Args:
            session: The session object
            question_id: ID of the question

        Returns:
            Question object if found, None otherwise
        """
        for question in session.questions:
            if question.id == question_id:
                return question
        return None
