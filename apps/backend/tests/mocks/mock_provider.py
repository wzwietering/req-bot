"""Mock LLM provider for testing without API calls."""

import uuid

from requirements_bot.core.models import (
    Answer,
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Requirement,
    Session,
)
from requirements_bot.providers.base import Provider


class MockProvider(Provider):
    """Mock provider that returns predictable responses for testing."""

    def __init__(self, model: str = "mock:test-model"):
        self.model = model
        self.question_counter = 0
        self.max_questions = 10

    def generate_single_question(self, prompt: str) -> Question | None:
        """Generate a mock question."""
        self.question_counter += 1

        if self.question_counter > self.max_questions:
            return None

        category = self._extract_category(prompt)

        return Question(
            id=str(uuid.uuid4()),
            text=f"Mock question {self.question_counter}: What are your requirements for {category}?",
            category=category,
            required=True,
        )

    def summarize_requirements(
        self, project: str, questions: list[Question], answers: list[Answer]
    ) -> list[Requirement]:
        """Generate mock requirements based on Q&A pairs."""
        requirements = []

        for i, (question, answer) in enumerate(zip(questions, answers, strict=False), 1):
            req = Requirement(
                id=str(uuid.uuid4()),
                title=f"REQ-{i}: {question.text[:50]}...",
                rationale=f"Based on answer: {answer.text[:100]}...",
                priority="MUST" if i <= 2 else "SHOULD" if i <= 4 else "COULD",
            )
            requirements.append(req)

        return requirements

    def analyze_answer(self, question: Question, answer: Answer, context: str = "") -> AnswerAnalysis:
        """Analyze answer quality with predictable logic."""
        answer_len = len(answer.text)

        # Determine answer quality based on length
        is_complete = answer_len >= 20
        is_specific = answer_len >= 30
        is_consistent = True  # Always consistent for mock

        # Generate follow-up questions for short answers
        follow_up_questions = []
        if answer_len < 50:
            follow_up_questions.append(f"Can you provide more details about: {answer.text[:30]}...?")

        analysis_notes = (
            f"Mock analysis: answer length {answer_len} chars. Complete: {is_complete}, Specific: {is_specific}"
        )

        return AnswerAnalysis(
            is_complete=is_complete,
            is_specific=is_specific,
            is_consistent=is_consistent,
            follow_up_questions=follow_up_questions,
            analysis_notes=analysis_notes,
        )

    def assess_completeness(self, session: Session) -> CompletenessAssessment:
        """Assess if enough information gathered with predictable logic."""
        qa_count = len(session.answers)
        total_answer_length = sum(len(a.text) for a in session.answers)

        is_complete = qa_count >= 3 and total_answer_length > 150
        confidence_score = min(0.95, qa_count * 0.25)

        missing_areas = []
        covered_categories = {a.category for q in session.questions for a in session.answers if a.question_id == q.id}

        required_categories = {"scope", "functionality", "constraints"}
        for cat in required_categories:
            if cat not in covered_categories:
                missing_areas.append(cat)

        return CompletenessAssessment(
            is_complete=is_complete,
            confidence_score=confidence_score,
            missing_areas=missing_areas,
            reasoning=(
                f"Based on {qa_count} Q&A pairs with total length {total_answer_length}, "
                f"assessment: {'complete' if is_complete else 'needs more information'}"
            ),
        )

    def _extract_category(self, prompt: str) -> str:
        """Extract category from prompt or use default."""
        categories = ["scope", "functionality", "constraints", "users", "integration"]

        for cat in categories:
            if cat in prompt.lower():
                return cat

        return categories[self.question_counter % len(categories)]
