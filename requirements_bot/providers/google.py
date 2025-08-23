import json
import os
from typing import List

from google import genai

from requirements_bot.core.models import (
    Answer,
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Requirement,
    Session,
)
from requirements_bot.core.prompts import (
    SYSTEM_INSTRUCTIONS,
    analyze_answer_prompt,
    assess_completeness_prompt,
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

    def analyze_answer(
        self, question: Question, answer: Answer, context: str = ""
    ) -> AnswerAnalysis:
        """Analyze answer quality and generate follow-up questions if needed."""

        prompt = analyze_answer_prompt(question.text, answer.text, context)
        full_prompt = f"{SYSTEM_INSTRUCTIONS['questions']}\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=full_prompt
            )

            content = response.text
            if not content:
                # Default analysis if no response
                return AnswerAnalysis(
                    is_complete=True,
                    is_specific=True,
                    is_consistent=True,
                    follow_up_questions=[],
                    analysis_notes="Analysis failed - defaulting to accepting answer",
                )

            analysis_data = json.loads(content)
            return AnswerAnalysis(**analysis_data)
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            print(f"Error parsing answer analysis response: {e}")
            # Default to accepting the answer if analysis fails
            return AnswerAnalysis(
                is_complete=True,
                is_specific=True,
                is_consistent=True,
                follow_up_questions=[],
                analysis_notes=f"Analysis error: {e}",
            )

    def assess_completeness(self, session: Session) -> CompletenessAssessment:
        """Assess if enough information has been gathered."""

        # Format the session context
        qa_history: list[str] = []
        for q, a in session.get_qa_history():
            answer_text = a.text if a else "No answer provided"
            qa_history.append(f"Q: {q.text}\nA: {answer_text}")

        session_context = "\n\n".join(qa_history)
        prompt = assess_completeness_prompt(session_context, len(session.questions))
        full_prompt = f"{SYSTEM_INSTRUCTIONS['requirements']}\n\n{prompt}"

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=full_prompt
            )

            content = response.text
            if not content:
                # Default assessment
                return CompletenessAssessment(
                    is_complete=len(session.questions) >= 8,
                    missing_areas=[],
                    confidence_score=0.5,
                    reasoning="Assessment failed - using basic heuristics",
                )

            assessment_data = json.loads(content)
            return CompletenessAssessment(**assessment_data)
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            print(f"Error parsing completeness assessment: {e}")
            # Fallback assessment
            return CompletenessAssessment(
                is_complete=len(session.questions) >= 8,
                missing_areas=[],
                confidence_score=0.5,
                reasoning=f"Assessment error: {e}",
            )
