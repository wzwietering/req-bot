import uuid

from requirements_bot.api.exceptions import InvalidSessionIdException
from requirements_bot.core.models import Session


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

    # Validate as proper UUID (comprehensive validation)
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise InvalidSessionIdException(session_id)

    return session_id
