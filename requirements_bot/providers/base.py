from requirements_bot.core.models import (
    Answer,
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Requirement,
    Session,
)


class Provider:
    @staticmethod
    def from_id(model_id: str) -> "Provider":
        # parse like "openai:gpt-5" / "anthropic:claude-4" / "google:gemini-2.5-pro"
        if ":" not in model_id:
            raise ValueError(
                f"Model ID must be in format 'vendor:model', got: '{model_id}'. "
                f"Use 'anthropic:claude-3-haiku-20240307' or similar."
            )

        vendor, model = model_id.split(":", 1)

        # Import mapping to avoid inline imports
        provider_map = {
            "openai": lambda: __import__("requirements_bot.providers.openai", fromlist=["ProviderImpl"]),
            "anthropic": lambda: __import__("requirements_bot.providers.anthropic", fromlist=["ProviderImpl"]),
            "google": lambda: __import__("requirements_bot.providers.google", fromlist=["ProviderImpl"]),
        }

        if vendor not in provider_map:
            raise ValueError(f"Unknown provider '{vendor}'")

        impl = provider_map[vendor]()
        return impl.ProviderImpl(model)

    def generate_questions(self, project: str, seed_questions: list[Question]) -> list[Question]: ...

    def summarize_requirements(
        self, project: str, questions: list[Question], answers: list[Answer]
    ) -> list[Requirement]: ...

    def analyze_answer(self, question: Question, answer: Answer, context: str = "") -> AnswerAnalysis:
        """Analyze answer quality and generate follow-up questions if needed."""
        ...

    def assess_completeness(self, session: Session) -> CompletenessAssessment:
        """Assess if enough information has been gathered."""
        ...
