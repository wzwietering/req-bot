# requirements_bot/core/prompts.py
from typing import List

from .models import Answer, Question


def generate_questions_prompt(project: str, seed_questions: List[Question]) -> str:
    """Generate a prompt for creating additional requirements questions."""

    # Format seed questions for the prompt
    seed_questions_text = ""
    if seed_questions:
        seed_questions_text = "\n".join(
            [
                f"- {q.text} (Category: {q.category}, Required: {q.required})"
                for q in seed_questions
            ]
        )

    return f"""You are a requirements engineering expert. Given a software project description and some existing questions, generate additional relevant questions to help gather comprehensive requirements.

Project: {project}

Existing questions:
{seed_questions_text}

Generate 5-8 additional questions that would help understand the requirements better. Focus on areas not covered by existing questions.

Return your response as a JSON array of objects with this structure:
{{
  "id": "unique_id",
  "text": "question text",
  "category": "one of: scope, users, constraints, nonfunctional, interfaces, data, risks, success",
  "required": true/false
}}

Only return the JSON array, no other text."""


def summarize_requirements_prompt(
    project: str, questions: List[Question], answers: List[Answer]
) -> str:
    """Generate a prompt for summarizing Q&A into formal requirements."""

    # Create a mapping of question ID to answer
    answer_map = {answer.question_id: answer.text for answer in answers}

    # Format Q&A pairs
    qa_pairs: List[str] = []
    for question in questions:
        answer_text = answer_map.get(question.id, "No answer provided")
        qa_pairs.append(f"Q: {question.text}\nA: {answer_text}\n")

    qa_text = "\n".join(qa_pairs)

    return f"""You are a requirements engineering expert. Based on the project description and the questions/answers provided, create a comprehensive list of formal requirements.

Project: {project}

Questions and Answers:
{qa_text}

Generate formal requirements that capture the essential needs identified through the Q&A process. Each requirement should be:
- Clear and unambiguous
- Testable/verifiable
- Appropriately prioritized

Return your response as a JSON array of objects with this structure:
{{
  "id": "unique_requirement_id",
  "title": "concise requirement title",
  "rationale": "explanation of why this requirement is needed (optional)",
  "priority": "MUST, SHOULD, or COULD"
}}

Only return the JSON array, no other text."""


# System instructions for different providers
SYSTEM_INSTRUCTIONS = {
    "questions": "You are a requirements engineering expert who responds only with valid JSON.",
    "requirements": "You are a requirements engineering expert who responds only with valid JSON.",
}
