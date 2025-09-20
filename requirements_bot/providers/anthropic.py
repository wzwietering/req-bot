import os

from anthropic import Anthropic

from requirements_bot.core.logging import span
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
from .exceptions import (
    FallbackFactory,
    extract_content_from_response,
    handle_provider_operation,
    parse_json_response,
)


class ProviderImpl(Provider):
    def __init__(self, model: str):
        self.model = model
        self.client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )

    def generate_questions(self, project: str, seed_questions: list[Question]) -> list[Question]:
        """Generate additional questions based on the project description and existing questions."""

        prompt = generate_questions_prompt(project, seed_questions)

        def _do_operation():
            with span(
                "llm.generate_questions",
                component="provider",
                operation="generate_questions",
                provider="anthropic",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    system=SYSTEM_INSTRUCTIONS["questions"],
                    messages=[{"role": "user", "content": prompt}],
                )

                content = extract_content_from_response(response, "anthropic")
                questions_data = parse_json_response(
                    content,
                    {
                        "operation": "generate_questions",
                        "provider": "anthropic",
                        "model": self.model,
                    },
                )
                return [Question(**q) for q in questions_data]

        return handle_provider_operation(
            operation="generate_questions",
            provider="anthropic",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=FallbackFactory.empty_questions_list,
        )

    def summarize_requirements(
        self, project: str, questions: list[Question], answers: list[Answer]
    ) -> list[Requirement]:
        """Summarize the questions and answers into formal requirements."""

        prompt = summarize_requirements_prompt(project, questions, answers)

        def _do_operation():
            with span(
                "llm.summarize_requirements",
                component="provider",
                operation="summarize_requirements",
                provider="anthropic",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    system=SYSTEM_INSTRUCTIONS["requirements"],
                    messages=[{"role": "user", "content": prompt}],
                )

                content = extract_content_from_response(response, "anthropic")
                requirements_data = parse_json_response(
                    content,
                    {
                        "operation": "summarize_requirements",
                        "provider": "anthropic",
                        "model": self.model,
                    },
                )
                return [Requirement(**req) for req in requirements_data]

        return handle_provider_operation(
            operation="summarize_requirements",
            provider="anthropic",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=FallbackFactory.empty_requirements_list,
        )

    def analyze_answer(self, question: Question, answer: Answer, context: str = "") -> AnswerAnalysis:
        """Analyze answer quality and generate follow-up questions if needed."""

        prompt = analyze_answer_prompt(question.text, answer.text, context)

        def _do_operation():
            with span(
                "llm.analyze_answer",
                component="provider",
                operation="analyze_answer",
                provider="anthropic",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=800,
                    system=SYSTEM_INSTRUCTIONS["questions"],
                    messages=[{"role": "user", "content": prompt}],
                )

                content = extract_content_from_response(response, "anthropic")
                analysis_data = parse_json_response(
                    content,
                    {
                        "operation": "analyze_answer",
                        "provider": "anthropic",
                        "model": self.model,
                    },
                )
                return AnswerAnalysis(**analysis_data)

        return handle_provider_operation(
            operation="analyze_answer",
            provider="anthropic",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=FallbackFactory.default_answer_analysis,
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

        def _do_operation():
            with span(
                "llm.assess_completeness",
                component="provider",
                operation="assess_completeness",
                provider="anthropic",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=600,
                    system=SYSTEM_INSTRUCTIONS["requirements"],
                    messages=[{"role": "user", "content": prompt}],
                )

                content = extract_content_from_response(response, "anthropic")
                assessment_data = parse_json_response(
                    content,
                    {
                        "operation": "assess_completeness",
                        "provider": "anthropic",
                        "model": self.model,
                    },
                )
                return CompletenessAssessment(**assessment_data)

        return handle_provider_operation(
            operation="assess_completeness",
            provider="anthropic",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=lambda: FallbackFactory.default_completeness_assessment(len(session.questions)),
        )
