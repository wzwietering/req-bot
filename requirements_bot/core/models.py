# requirements_bot/core/models.py
from typing import Literal, Optional

from pydantic import BaseModel


class Question(BaseModel):
    id: str
    text: str
    category: Literal[
        "scope",
        "users",
        "constraints",
        "nonfunctional",
        "interfaces",
        "data",
        "risks",
        "success",
    ]
    required: bool = True


class Answer(BaseModel):
    question_id: str
    text: str


class Requirement(BaseModel):
    id: str
    title: str
    rationale: Optional[str] = None
    priority: Literal["MUST", "SHOULD", "COULD"] = "MUST"


class Session(BaseModel):
    project: str
    questions: list[Question]
    answers: list[Answer] = []
    requirements: list[Requirement] = []

    def to_markdown(self) -> str:
        """Generate a Markdown document from the session data."""
        lines: list[str] = []

        # Title and project description
        lines.append("# Requirements Document")
        lines.append("")
        lines.append("## Project Description")
        lines.append("")
        lines.append(self.project)
        lines.append("")

        # Create a mapping of question ID to answer for easy lookup
        answer_map: dict[str, Answer] = {
            answer.question_id: answer for answer in self.answers
        }

        # Questions and Answers section
        if self.questions:
            lines.append("## Questions and Answers")
            lines.append("")

            # Group questions by category
            categories: dict[str, list[Question]] = {}
            for question in self.questions:
                if question.category not in categories:
                    categories[question.category] = []
                categories[question.category].append(question)

            # Sort categories for consistent output
            category_order = [
                "scope",
                "users",
                "constraints",
                "nonfunctional",
                "interfaces",
                "data",
                "risks",
                "success",
            ]

            for category in category_order:
                if category in categories:
                    lines.append(f"### {category.title()}")
                    lines.append("")

                    for question in categories[category]:
                        lines.append(f"**Q: {question.text}**")
                        lines.append("")

                        answer = answer_map.get(question.id)
                        if answer:
                            lines.append(f"A: {answer.text}")
                        else:
                            lines.append("A: *No answer provided*")

                        lines.append("")

        # Requirements section
        if self.requirements:
            lines.append("## Requirements")
            lines.append("")

            # Group requirements by priority
            priority_groups: dict[str, list[Requirement]] = {
                "MUST": [],
                "SHOULD": [],
                "COULD": [],
            }
            for req in self.requirements:
                priority_groups[req.priority].append(req)

            for priority in ["MUST", "SHOULD", "COULD"]:
                reqs = priority_groups[priority]
                if reqs:
                    lines.append(f"### {priority} Requirements")
                    lines.append("")

                    for req in reqs:
                        lines.append(f"**{req.id}: {req.title}**")
                        lines.append("")

                        if req.rationale:
                            lines.append(f"*Rationale:* {req.rationale}")
                            lines.append("")

                        lines.append("")

        return "\n".join(lines)
