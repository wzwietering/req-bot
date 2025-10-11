import uuid

from requirements_bot.core.constants import MIN_QUEUE_SIZE, QUESTIONS_PER_AREA
from requirements_bot.core.models import Question, Session

# Requirement areas that should be covered in every interview
REQUIREMENT_AREAS = [
    "scope",
    "users",
    "constraints",
    "nonfunctional",
    "interfaces",
    "data",
    "risks",
    "success",
]


class QuestionQueue:
    def __init__(self):
        self.questions: list[Question] = []

    def should_generate_more(self, session: Session) -> bool:
        """Check if we need to generate more questions based on queue size."""
        unanswered = self._get_unanswered_questions(session)
        return len(unanswered) < MIN_QUEUE_SIZE

    def get_next_target_area(self, session: Session) -> str | None:
        """Determine which requirement area to ask about next based on coverage."""
        area_counts = self._get_area_coverage_stats(session)

        # Find the least covered area
        for area in REQUIREMENT_AREAS:
            if area_counts[area] < QUESTIONS_PER_AREA:
                return area

        # All areas sufficiently covered
        return None

    def get_area_coverage_stats(self, session: Session) -> dict[str, int]:
        """Get statistics on how many questions have been asked per area."""
        return self._get_area_coverage_stats(session)

    def add_questions(self, new_questions: list[Question], existing_questions: list[Question]) -> list[Question]:
        """Add new questions, filtering out duplicates."""
        return self.filter_similar_questions(new_questions, existing_questions)

    def insert_followups(self, follow_up_texts: list[str], base_question: Question, session: Session) -> list[Question]:
        """Create follow-up questions based on the base question."""
        follow_up_questions: list[Question] = []
        for _, follow_up_text in enumerate(follow_up_texts):
            follow_up_id = str(uuid.uuid4())
            follow_up = Question(
                id=follow_up_id,
                text=follow_up_text,
                category=base_question.category,
                required=False,
            )
            follow_up_questions.append(follow_up)
            session.questions.append(follow_up)
        return follow_up_questions

    def filter_asked_questions(self, new_questions: list[Question], session: Session) -> list[Question]:
        """Filter out questions that have already been asked."""
        asked_texts = {q.text.lower() for q in session.questions}
        return [q for q in new_questions if q.text.lower() not in asked_texts]

    def filter_similar_questions(
        self, new_questions: list[Question], existing_questions: list[Question]
    ) -> list[Question]:
        """Filter out questions that are too similar to existing ones."""
        existing_texts = {q.text for q in existing_questions}
        return [q for q in new_questions if q.text not in existing_texts]

    def _get_unanswered_questions(self, session: Session) -> list[Question]:
        """Get all questions that haven't been answered yet."""
        answered_ids = {a.question_id for a in session.answers}
        return [q for q in session.questions if q.id not in answered_ids]

    def _get_area_coverage_stats(self, session: Session) -> dict[str, int]:
        """Count how many questions have been asked for each area."""
        stats: dict[str, int] = {}
        for q in session.questions:
            if q.category in REQUIREMENT_AREAS:
                stats[q.category] = stats.get(q.category, 0) + 1
        # Ensure all areas are in the dict
        for area in REQUIREMENT_AREAS:
            if area not in stats:
                stats[area] = 0
        return stats
