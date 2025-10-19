from specscribe.core.logging import span
from specscribe.core.models import Answer, Question
from specscribe.providers.base import Provider


def generate_requirements(
    provider: Provider,
    project: str,
    questions: list[Question],
    answers: list[Answer],
    session_id: str,
    model_id: str,
):
    with span(
        "llm.summarize_requirements",
        component="pipeline",
        operation="summarize_requirements",
        session_id=session_id,
        provider_model=model_id,
        answers=len(answers),
        questions=len(questions),
    ):
        return provider.summarize_requirements(project, questions, answers)


# Presentation logic moved to IoInterface implementations.
# Use io.print_interview_header() and io.print_requirements_generation() instead.
