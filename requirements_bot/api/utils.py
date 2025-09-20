import re
import uuid

from requirements_bot.api.exceptions import InvalidSessionIdException
from requirements_bot.core.models import Question, Session


def get_current_question(session: Session) -> Question | None:
    """Get the current unanswered question for a session."""
    answered_question_ids = {answer.question_id for answer in session.answers}
    for question in session.questions:
        if question.id not in answered_question_ids:
            return question
    return None


def get_next_question(session: Session) -> Question | None:
    """Get the next unanswered question for a session."""
    return get_current_question(session)


def calculate_session_progress(session: Session) -> tuple[int, int, int, float]:
    """Calculate session progress metrics.

    Returns:
        tuple: (total_questions, answered_questions, remaining_questions, completion_percentage)
    """
    total_questions = len(session.questions)
    answered_questions = len(session.answers)
    remaining_questions = total_questions - answered_questions
    completion_percentage = (answered_questions / total_questions * 100) if total_questions > 0 else 0

    return total_questions, answered_questions, remaining_questions, completion_percentage


def validate_session_id(session_id: str) -> str:
    """Validate session ID format and return cleaned ID.

    Args:
        session_id: The session ID to validate

    Returns:
        str: The validated session ID

    Raises:
        InvalidSessionIdException: If session ID format is invalid
    """
    if not session_id or not isinstance(session_id, str):
        raise InvalidSessionIdException(str(session_id))

    # Remove whitespace
    session_id = session_id.strip()

    # Check length (reasonable limits)
    if len(session_id) < 8 or len(session_id) > 128:
        raise InvalidSessionIdException(session_id)

    # Check for basic alphanumeric pattern with hyphens/underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
        raise InvalidSessionIdException(session_id)

    # Try to parse as UUID if it looks like one
    if "-" in session_id and len(session_id) == 36:
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise InvalidSessionIdException(session_id)

    return session_id
