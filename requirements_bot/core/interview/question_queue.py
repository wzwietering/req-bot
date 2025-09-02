import random

from requirements_bot.core.models import Question, Session

CANNED_SEED_QUESTIONS = [
    ("scope", "What problem are we solving?"),
    ("users", "Who are the primary users and their key jobs?"),
    ("constraints", "What platform, budget, or timeline constraints exist?"),
    ("nonfunctional", "Any performance, security, or compliance needs?"),
    ("interfaces", "What external systems or APIs must we integrate with?"),
    ("data", "What data do we store, and what is the source of truth?"),
    ("risks", "Top 3 risks or unknowns?"),
    ("success", "How will we measure success?"),
]


class QuestionQueue:
    def __init__(self):
        self.questions: list[Question] = []

    def initialize_from_seeds(self, shuffled: bool = True) -> list[Question]:
        seed_questions = [
            Question(id=f"q{i}", category=c, text=t, required=True)
            for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
        ]

        if shuffled:
            shuffled_seeds = seed_questions.copy()
            random.shuffle(shuffled_seeds)
            return shuffled_seeds
        return seed_questions

    def add_questions(
        self, new_questions: list[Question], existing_questions: list[Question]
    ) -> list[Question]:
        return self.filter_similar_questions(new_questions, existing_questions)

    def insert_followups(
        self, follow_up_texts: list[str], base_question: Question, session: Session
    ) -> list[Question]:
        follow_up_questions: list[Question] = []
        for i, follow_up_text in enumerate(follow_up_texts):
            follow_up_id = f"followup_{base_question.id}_{i}"
            follow_up = Question(
                id=follow_up_id,
                text=follow_up_text,
                category=base_question.category,
                required=False,
            )
            follow_up_questions.append(follow_up)
            session.questions.append(follow_up)
        return follow_up_questions

    def filter_asked_questions(
        self, new_questions: list[Question], session: Session
    ) -> list[Question]:
        asked_texts = {q.text.lower() for q in session.questions}
        return [q for q in new_questions if q.text.lower() not in asked_texts]

    def filter_similar_questions(
        self, new_questions: list[Question], existing_questions: list[Question]
    ) -> list[Question]:
        existing_texts = {q.text for q in existing_questions}
        return [q for q in new_questions if q.text not in existing_texts]
