from requirements_bot.core.interview.question_queue import QuestionQueue
from requirements_bot.core.io_interface import IOInterface, RichConsoleIO
from requirements_bot.core.logging import log_event, mask_text, span
from requirements_bot.core.models import (
    Answer,
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Session,
)
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.providers.base import Provider


class InterviewConductor:
    def __init__(
        self,
        provider: Provider,
        session_manager: SessionManager,
        question_queue: QuestionQueue,
        io: IOInterface | None = None,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.question_queue = question_queue
        self.io = io or RichConsoleIO()

    def present_question(self, question: Question, question_number: int, total_questions: int) -> None:
        self.io.print(f"\n[{question_number}/{total_questions}] [{question.category.upper()}] {question.text}")

    def collect_user_input(self) -> str:
        return self.io.input("> ")

    def analyze_response(self, question: Question, answer: Answer, session: Session, model_id: str):
        context = session.get_context_for_question(question.id)
        with span(
            "llm.analyze_answer",
            component="pipeline",
            operation="analyze_answer",
            session_id=session.id,
            provider_model=model_id,
            question_id=question.id,
            category=question.category,
            answer_len=len(answer.text),
        ):
            return self.provider.analyze_answer(question, answer, context)

    def update_answer_metadata(self, answer: Answer, analysis: AnswerAnalysis) -> None:
        answer.is_vague = not (analysis.is_complete and analysis.is_specific)
        answer.needs_followup = bool(analysis.follow_up_questions)

    def log_answer_received(self, session: Session, question: Question, answer_text: str) -> None:
        log_event(
            "answer.received",
            component="pipeline",
            operation="answer",
            session_id=session.id,
            question_id=question.id,
            category=question.category,
            text_len=len(answer_text),
            preview=mask_text(answer_text)[:80],
        )

    def should_check_completeness(self, question_counter: int, queue_length: int) -> bool:
        return (question_counter % 5 == 0 and question_counter >= 5) or (queue_length == 0 and question_counter >= 5)

    def assess_interview_status(self, session: Session, model_id: str):
        with span(
            "llm.assess_completeness",
            component="pipeline",
            operation="assess_completeness",
            session_id=session.id,
            provider_model=model_id,
            qa_count=len(session.questions),
        ):
            return self.provider.assess_completeness(session)

    def handle_completion(self, completeness: CompletenessAssessment) -> bool:
        self.io.print(f"\n✓ Assessment: {completeness.reasoning}")
        return True

    def handle_missing_areas(self, completeness: CompletenessAssessment) -> None:
        if completeness.missing_areas:
            self.io.print(f"\n⚠ Still need info on: {', '.join(completeness.missing_areas)}")

    def process_followups(
        self,
        analysis: AnswerAnalysis,
        question: Question,
        session: Session,
        question_queue: list[Question],
    ) -> list[Question]:
        if not analysis.follow_up_questions:
            return question_queue

        follow_ups = self.question_queue.insert_followups(analysis.follow_up_questions, question, session)

        if analysis.analysis_notes:
            self.io.print(f"   → I need to ask a follow-up: {analysis.analysis_notes}")

        return follow_ups + question_queue
