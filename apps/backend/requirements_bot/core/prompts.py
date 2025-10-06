from .models import Answer, Question


def generate_single_question_prompt(project: str, target_area: str, context: str = "") -> str:
    """Generate ONE question for a specific requirement area with full context."""

    area_descriptions = {
        "scope": "the core problem, user pain points, and solution boundaries",
        "users": "who will use this, their roles, workflows, and motivations",
        "constraints": "platform, technology, budget, timeline, or resource limits",
        "nonfunctional": "performance, security, compliance, scalability needs",
        "interfaces": "external systems, APIs, integrations, data sources",
        "data": "what data to store, schemas, sources of truth, data flows",
        "risks": "technical risks, unknowns, assumptions that need validation",
        "success": "measurable outcomes, KPIs, definition of done",
    }

    context_section = ""
    if context:
        context_section = f"""
Previous conversation:
{context}

"""

    return f"""You are a requirements engineering expert conducting a natural, conversational interview.

Project: {project}

{context_section}Focus Area: {area_descriptions.get(target_area, target_area)}

Based on the conversation so far, generate ONE insightful question about {target_area}.

Requirements:
- Make it conversational and natural, not formal or checklist-like
- Build on what you've learned from previous answers
- Ask about concrete specifics that will lead to actionable requirements
- Frame it to challenge assumptions and dig deeper
- Make the user feel understood

Return as JSON:
{{
  "id": "unique_id",
  "text": "your question",
  "category": "{target_area}",
  "required": false
}}

Only return the JSON, nothing else."""


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
        f"""You are a requirements engineering expert. """
        f"""Analyze this answer to determine if follow-up questions are TRULY necessary.

{context_section}Current Q&A:
Q: {question}
A: {answer}

Generate follow-ups ONLY if:
1. Answer is completely vague ("I don't know", "maybe", "it depends") with NO concrete details
2. Answer directly contradicts previous statements
3. Answer completely avoids the question

DO NOT generate follow-ups if:
- Answer provides reasonable business-level information (even if brief)
- Answer gives concrete examples or specifics
- You just want "more detail" (we can ask new questions later for different areas)
- The topic is already well-covered in previous answers
- The answer is acceptable but not perfect

Be VERY conservative. Most answers should need 0 follow-ups. Maximum 2 follow-ups even if needed.

Examples of ACCEPTABLE answers that need NO follow-up:
- "Tool reuse indicates success" (valid success metric)
- "Python packages with API keys" (sufficient for integration requirements)
- "Web-based application" (adequate platform specification)
- "Small team of 5 developers" (sufficient user description)
- Any answer with concrete nouns, numbers, or specific examples

Return JSON:
{{
  "needs_clarification": true/false,
  "follow_up_questions": ["question1", "question2"] or [],
  "reasoning": "why follow-ups are truly necessary (required if needs_clarification is true)"
}}

Only return JSON, no other text."""
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
