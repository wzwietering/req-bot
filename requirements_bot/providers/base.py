from typing import List
from requirements_bot.core.models import Answer, Question, Requirement

class Provider:
    @staticmethod
    def from_id(model_id: str) -> "Provider":
        # parse like "openai:gpt-4o-mini" / "anthropic:claude-3-5" / "google:gemini-1.5-pro"
        vendor, model = model_id.split(":", 1)
        if vendor == "openai":
            from . import openai as impl
        elif vendor == "anthropic":
            from . import anthropic as impl
        elif vendor == "google":
            from . import google as impl
        else:
            raise ValueError(f"Unknown provider '{vendor}'")
        return impl.ProviderImpl(model)

    async def generate_questions(self, project: str, seed_questions: List[Question]) -> List[Question]: ...
    async def summarize_requirements(self, project: str, questions: List[Question], answers: List[Answer]) -> List[Requirement]: ...
