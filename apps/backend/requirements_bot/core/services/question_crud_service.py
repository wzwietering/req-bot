"""CRUD service for Question management."""

from uuid import uuid4

from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.services.exceptions import QuestionNotFoundError, SessionCompleteError
from requirements_bot.core.services.question_service import QuestionCategory
from requirements_bot.core.storage import StorageInterface


class QuestionCRUDService:
    """Service for question CRUD operations."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def get_question(self, session: Session, question_id: str) -> Question | None:
        """Get a specific question by ID within a session.

        Args:
            session: The session object
            question_id: ID of the question to retrieve

        Returns:
            Question object if found, None otherwise
        """
        return next((q for q in session.questions if q.id == question_id), None)

    def list_questions(self, session: Session) -> list[Question]:
        """List all questions for a session.

        Args:
            session: The session object

        Returns:
            List of Question objects
        """
        return session.questions

    def create_question(
        self, session: Session, text: str, category: QuestionCategory, required: bool = True
    ) -> tuple[Session, Question]:
        """Create a new question for a session.

        Args:
            session: The session object
            text: Question text
            category: Question category
            required: Whether the question is required

        Returns:
            Tuple of (updated session, new question)

        Raises:
            SessionCompleteError: If session is complete
        """
        if session.conversation_complete:
            raise SessionCompleteError("add questions to")

        # Generate unique question ID
        question_id = f"q_{uuid4().hex[:8]}"

        # Create new question
        new_question = Question(id=question_id, text=text, category=category, required=required)

        # Add to session
        session.questions.append(new_question)

        # Save session
        self.storage.save_session(session)

        return session, new_question

    def update_question(
        self,
        session: Session,
        question_id: str,
        text: str | None = None,
        category: QuestionCategory | None = None,
        required: bool | None = None,
    ) -> tuple[Session, Question]:
        """Update an existing question.

        Args:
            session: The session object
            question_id: ID of the question to update
            text: New question text (if provided)
            category: New category (if provided)
            required: New required status (if provided)

        Returns:
            Tuple of (updated session, updated question)

        Raises:
            SessionCompleteError: If session is complete
            QuestionNotFoundError: If question not found
        """
        if session.conversation_complete:
            raise SessionCompleteError("update questions in")

        # Find the question and its index in one pass
        question_with_index = next(((i, q) for i, q in enumerate(session.questions) if q.id == question_id), None)

        if question_with_index is None:
            raise QuestionNotFoundError(question_id)

        index, old_question = question_with_index

        # Create updated question with new values
        updated_question = Question(
            id=old_question.id,
            text=text if text is not None else old_question.text,
            category=category if category is not None else old_question.category,
            required=required if required is not None else old_question.required,
        )
        session.questions[index] = updated_question

        # Save session
        self.storage.save_session(session)

        return session, updated_question

    def delete_question(self, session: Session, question_id: str) -> Session:
        """Delete a question from a session.

        This will also cascade delete any associated answer.

        Args:
            session: The session object
            question_id: ID of the question to delete

        Returns:
            Updated session

        Raises:
            SessionCompleteError: If session is complete
            QuestionNotFoundError: If question not found
        """
        if session.conversation_complete:
            raise SessionCompleteError("delete questions from")

        # Check if question exists
        question = self.get_question(session, question_id)
        if not question:
            raise QuestionNotFoundError(question_id)

        # IMPORTANT: Remove associated answer FIRST, before removing question
        # This ensures the synchronizer deletes the answer before trying to delete
        # the question, avoiding foreign key constraint issues
        session.answers = [a for a in session.answers if a.question_id != question_id]

        # Then remove question from list
        session.questions = [q for q in session.questions if q.id != question_id]

        # Save session (synchronizers will handle database deletions in correct order)
        self.storage.save_session(session)

        return session

    def get_answer_for_question(self, session: Session, question_id: str) -> Answer | None:
        """Get the answer for a specific question.

        Args:
            session: The session object
            question_id: ID of the question

        Returns:
            Answer object if found, None otherwise
        """
        return next((a for a in session.answers if a.question_id == question_id), None)
