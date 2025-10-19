"""Service for generating and managing questions."""

import uuid
from typing import Literal

from specscribe.core.models import Question

QuestionCategory = Literal["scope", "users", "constraints", "nonfunctional", "interfaces", "data", "risks", "success"]


class QuestionService:
    """Service for generating questions for requirements gathering sessions."""

    @staticmethod
    def generate_basic_questions(project: str) -> list[Question]:
        """Generate basic questions for a new project session."""
        basic_questions: list[tuple[str, QuestionCategory]] = [
            ("What is the main purpose of this project?", "scope"),
            ("Who are the target users or stakeholders?", "users"),
            ("What are the key features you want to include?", "scope"),
            ("Are there any specific technical requirements or constraints?", "constraints"),
            ("What interfaces or integrations are needed?", "interfaces"),
        ]

        return [Question(id=str(uuid.uuid4()), text=text, category=category) for text, category in basic_questions]
