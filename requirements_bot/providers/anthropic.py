import json
import os
from typing import List

from anthropic import Anthropic

from requirements_bot.core.models import Answer, Question, Requirement
from requirements_bot.core.prompts import (
    SYSTEM_INSTRUCTIONS,
    generate_questions_prompt,
    summarize_requirements_prompt,
)

from .base import Provider


class ProviderImpl(Provider):
    def __init__(self, model: str):
        self.model = model
        self.client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

    def generate_questions(
        self, project: str, seed_questions: List[Question]
    ) -> List[Question]:
        """Generate additional questions based on the project description and existing questions."""

        prompt = generate_questions_prompt(project, seed_questions)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=SYSTEM_INSTRUCTIONS["questions"],
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract the text content from the response
            content = ""
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        content += block.text

            if not content:
                return []

            questions_data = json.loads(content)
            return [Question(**q) for q in questions_data]
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing Anthropic response: {e}")
            return []

    def summarize_requirements(
        self, project: str, questions: List[Question], answers: List[Answer]
    ) -> List[Requirement]:
        """Summarize the questions and answers into formal requirements."""

        prompt = summarize_requirements_prompt(project, questions, answers)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=SYSTEM_INSTRUCTIONS["requirements"],
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract the text content from the response
            content = ""
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        content += block.text

            if not content:
                return []

            requirements_data = json.loads(content)
            return [Requirement(**req) for req in requirements_data]
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing Anthropic response: {e}")
            return []
