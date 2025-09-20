from requirements_bot.core.logging import span
from requirements_bot.core.models import Answer, Question
from requirements_bot.providers.base import Provider


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


def print_interview_header(mode: str, remaining_questions: int) -> None:
    if mode == "conversational":
        print("\n=== Starting conversational interview ===")
        print(
            "I'll ask questions to understand your requirements. I may ask follow-up questions based on your answers."
        )
        print("💡 Tip: Type 'exit', 'quit', or 'done' to save your progress and exit anytime.")
    else:
        print(
            f"\n=== Starting interview with {remaining_questions} remaining questions ==="
        )
        print("💡 Tip: Type 'exit', 'quit', or 'done' to save your progress and exit anytime.")


def print_requirements_generation(answer_count: int) -> None:
    print(f"\n=== Generating requirements from {answer_count} answers ===")
