import json
import os
from typing import List

from openai import OpenAI

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
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    def generate_questions(
        self, project: str, seed_questions: List[Question]
    ) -> List[Question]:
        """Generate additional questions based on the project description and existing questions."""

        prompt = generate_questions_prompt(project, seed_questions)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            instructions=SYSTEM_INSTRUCTIONS["questions"],
            temperature=0.7,
        )

        try:
            content = response.output_text
            questions_data = json.loads(content)
            return [Question(**q) for q in questions_data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing OpenAI response: {e}")
            return []

    def summarize_requirements(
        self, project: str, questions: List[Question], answers: List[Answer]
    ) -> List[Requirement]:
        """Summarize the questions and answers into formal requirements."""

        prompt = summarize_requirements_prompt(project, questions, answers)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            instructions=SYSTEM_INSTRUCTIONS["requirements"],
            temperature=0.3,  # Lower temperature for more consistent output
        )

        try:
            content = response.output_text
            requirements_data = json.loads(content)
            return [Requirement(**req) for req in requirements_data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing OpenAI response: {e}")
            return []
