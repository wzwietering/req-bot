import os
import uuid

from openai import OpenAI

from specscribe.core.logging import span
from specscribe.core.models import (
    Answer,
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Requirement,
    Session,
)
from specscribe.core.prompts import (
    SYSTEM_INSTRUCTIONS,
    analyze_answer_prompt,
    assess_completeness_prompt,
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
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )

    def generate_single_question(self, prompt: str) -> Question | None:
        """Generate a single question using a custom prompt."""

        def _do_operation():
            with span(
                "llm.generate_single_question",
                component="provider",
                operation="generate_single_question",
                provider="openai",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    instructions=SYSTEM_INSTRUCTIONS["questions"],
                    temperature=0.7,
                )

                content = extract_content_from_response(response, "openai")
                question_data = parse_json_response(
                    content,
                    {
                        "operation": "generate_single_question",
                        "provider": "openai",
                        "model": self.model,
                    },
                )

                # The response should be a single question object, not an array
                if isinstance(question_data, list) and len(question_data) > 0:
                    question_data = question_data[0]
                elif not isinstance(question_data, dict):
                    return None

                return Question(
                    id=str(uuid.uuid4()),
                    text=question_data["text"],
                    category=question_data["category"],
                    required=question_data.get("required", False),
                )

        return handle_provider_operation(
            operation="generate_single_question",
            provider="openai",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=lambda: None,
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
                provider="openai",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    instructions=SYSTEM_INSTRUCTIONS["requirements"],
                    temperature=0.3,  # Lower temperature for more consistent output
                )

                content = extract_content_from_response(response, "openai")
                requirements_data = parse_json_response(
                    content,
                    {
                        "operation": "summarize_requirements",
                        "provider": "openai",
                        "model": self.model,
                    },
                )
                return [Requirement(**req) for req in requirements_data]

        return handle_provider_operation(
            operation="summarize_requirements",
            provider="openai",
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
                provider="openai",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    instructions=SYSTEM_INSTRUCTIONS["questions"],
                    temperature=0.3,
                )

                content = extract_content_from_response(response, "openai")
                analysis_data = parse_json_response(
                    content,
                    {
                        "operation": "analyze_answer",
                        "provider": "openai",
                        "model": self.model,
                    },
                )
                return AnswerAnalysis(**analysis_data)

        return handle_provider_operation(
            operation="analyze_answer",
            provider="openai",
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
                provider="openai",
                model=self.model,
                prompt_len=len(prompt),
            ):
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    instructions=SYSTEM_INSTRUCTIONS["requirements"],
                    temperature=0.2,
                )

                content = extract_content_from_response(response, "openai")
                assessment_data = parse_json_response(
                    content,
                    {
                        "operation": "assess_completeness",
                        "provider": "openai",
                        "model": self.model,
                    },
                )
                return CompletenessAssessment(**assessment_data)

        return handle_provider_operation(
            operation="assess_completeness",
            provider="openai",
            model=self.model,
            operation_func=_do_operation,
            fallback_factory=lambda: FallbackFactory.default_completeness_assessment(len(session.questions)),
        )
