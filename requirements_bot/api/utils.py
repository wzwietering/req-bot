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
