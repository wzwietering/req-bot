from .models import Answer, Question


def generate_questions_prompt(project: str, seed_questions: list[Question]) -> str:
    """Generate a prompt for creating additional requirements questions."""

    # Format seed questions for the prompt
    seed_questions_text = ""
    if seed_questions:
        seed_questions_text = "\n".join(
            [f"- {q.text} (Category: {q.category}, Required: {q.required})" for q in seed_questions]
        )

    return (
        f"""You are a requirements engineering expert. Given a software project description and existing questions, """
        f"""generate additional relevant questions to help gather comprehensive requirements.

Project: {project}

Existing questions:
{seed_questions_text}

Generate 5-8 additional questions that would help understand the requirements better.
Focus on areas not covered by existing questions.

Return your response as a JSON array of objects with this structure:
{{
  "id": "unique_id",
  "text": "question text",
  "category": "one of: scope, users, constraints, nonfunctional, interfaces, data, risks, success",
  "required": true/false
}}

Only return the JSON array, no other text."""
    )


def summarize_requirements_prompt(project: str, questions: list[Question], answers: list[Answer]) -> str:
    """Generate a prompt for summarizing Q&A into formal requirements."""

    # Create a mapping of question ID to answer
    answer_map = {answer.question_id: answer.text for answer in answers}

    # Format Q&A pairs
    qa_pairs: list[str] = []
    for question in questions:
        answer_text = answer_map.get(question.id, "No answer provided")
        qa_pairs.append(f"Q: {question.text}\nA: {answer_text}\n")

    qa_text = "\n".join(qa_pairs)

    return (
        f"""You are a requirements engineering expert. Based on the project description and questions/answers, """
        f"""create a comprehensive list of formal requirements.

Project: {project}

Questions and Answers:
{qa_text}

Generate formal requirements that capture the essential needs identified through the Q&A process.
Each requirement should be:
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
    )


def analyze_answer_prompt(question: str, answer: str, context: str = "") -> str:
    """Generate a prompt for analyzing answer quality and generating follow-ups."""

    context_section = ""
    if context.strip():
        context_section = f"""
Previous conversation context:
{context}

"""

    return (
        f"""You are a requirements engineering expert. Analyze this Q&A pair for completeness and clarity """
        f"""from a HIGH-LEVEL REQUIREMENTS perspective.

{context_section}Current Q&A:
Q: {question}
A: {answer}

Remember: We are gathering BUSINESS REQUIREMENTS, not implementation details. Evaluate this answer:

1. **Complete**: Does it identify the key business need or constraint?
2. **Specific**: Is it concrete enough for requirements?
3. **Consistent**: Does it align with previous answers?

ONLY generate follow-up questions if the answer is:
- Extremely vague with no concrete elements (e.g., "maybe", "I don't know", "it depends")
- Contradicts previous answers
- Completely avoids answering the question

DO NOT ask for follow-ups when answers provide reasonable business-level information, even if not highly detailed.
Examples of ACCEPTABLE answers that need NO follow-up:
- "Tool reuse indicates success" (valid success metric)
- "Python packages with API keys" (sufficient for integration requirements)
- "Web-based application" (adequate platform specification)
- "Small team of 5 developers" (sufficient user description)

Return your analysis as JSON with this structure:
{{
  "is_complete": true/false,
  "is_specific": true/false,
  "is_consistent": true/false,
  "follow_up_questions": ["question1", "question2", ...],
  "analysis_notes": "brief explanation of issues found"
}}

Only return the JSON, no other text."""
    )


def assess_completeness_prompt(session_context: str, total_questions: int) -> str:
    """Generate a prompt for assessing if enough information has been gathered."""

    return (
        f"""You are a requirements engineering expert. Review this Q&A session to determine """
        f"""if enough information has been gathered to write comprehensive requirements.

Session overview:
- Total questions asked: {total_questions}

Q&A History:
{session_context}

Evaluate if we have sufficient information to create a complete requirements document. Consider:
1. Are core areas covered (scope, users, constraints, technical needs)?
2. Are there any critical gaps that would prevent understanding the business problem?
3. Do we have enough information to write meaningful requirements?

Be reasonable.

Return your assessment as JSON:
{{
  "is_complete": true/false,
  "missing_areas": ["area1", "area2", ...],
  "confidence_score": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Only return the JSON, no other text."""
    )


# System instructions for different providers
SYSTEM_INSTRUCTIONS = {
    "questions": "You are a requirements engineering expert who responds only with valid JSON.",
    "requirements": "You are a requirements engineering expert who responds only with valid JSON.",
}
