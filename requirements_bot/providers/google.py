import json
import os
from typing import List

from google import genai

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
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    def generate_questions(
        self, project: str, seed_questions: List[Question]
    ) -> List[Question]:
        """Generate additional questions based on the project description and existing questions."""

        prompt = generate_questions_prompt(project, seed_questions)

        # Create the full prompt with system instructions
        full_prompt = f"{SYSTEM_INSTRUCTIONS['questions']}\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=full_prompt
            )

            content = response.text
            if not content:
                return []

            questions_data = json.loads(content)
            return [Question(**q) for q in questions_data]
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing Google Gemini response: {e}")
            return []

    def summarize_requirements(
        self, project: str, questions: List[Question], answers: List[Answer]
    ) -> List[Requirement]:
        """Summarize the questions and answers into formal requirements."""

        prompt = summarize_requirements_prompt(project, questions, answers)

        # Create the full prompt with system instructions
        full_prompt = f"{SYSTEM_INSTRUCTIONS['requirements']}\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=full_prompt
            )

            content = response.text
            if not content:
                return []

            requirements_data = json.loads(content)
            return [Requirement(**req) for req in requirements_data]
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            # Fallback to empty list if parsing fails
            print(f"Error parsing Google Gemini response: {e}")
            return []
