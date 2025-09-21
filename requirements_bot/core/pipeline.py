import logging
import random

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.interview.interview_conductor import InterviewConductor
from requirements_bot.core.interview.question_queue import QuestionQueue
from requirements_bot.core.interview.utils import generate_requirements
from requirements_bot.core.interview_constants import EXIT_SIGNAL
from requirements_bot.core.io_interface import RichConsoleIO
from requirements_bot.core.logging import log_event, span
from requirements_bot.core.models import Answer, Session
from requirements_bot.core.services import (
    CompletenessAssessmentService,
    InterviewLoopManager,
    QuestionGenerationService,
    SessionFinalizationService,
    SessionSetupManager,
)
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.core.storage_interface import StorageInterface
from requirements_bot.providers.base import Provider


def run_interview(
    project: str,
    model_id: str,
    session_id: str | None = None,
    storage: StorageInterface | None = None,
) -> Session:
    provider = Provider.from_id(model_id)
    session_manager = SessionManager(storage)
    question_queue = QuestionQueue()
    io = RichConsoleIO(session_id=session_id)
    conductor = InterviewConductor(provider, session_manager, question_queue, io)

    session_manager.setup_logging_context()

    session: Session | None = None
    if session_id:
        session = session_manager.load_existing_session(session_id, "simple")

    if session:
        # Transition to waiting for input state if resuming
        session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        answered_question_ids = {a.question_id for a in session.answers}
        all_qs = [q for q in session.questions if q.id not in answered_question_ids]
    else:
        if session_id:
            io.print_session_message(f"Session {session_id} not found, starting new interview", is_warning=True)

        seed_questions = question_queue.initialize_from_seeds(shuffled=False)
        session = session_manager.create_new_session(project, [], "simple")

        session_manager.state_manager.create_checkpoint(session, "generate_questions")
        try:
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=model_id,
                seed_count=len(seed_questions),
            ):
                llm_questions = provider.generate_questions(project, seed_questions=seed_questions)
            filtered_questions = question_queue.add_questions(llm_questions, seed_questions)
        except Exception as e:
            # If LLM question generation fails, log the error and continue with just seed questions
            log_event(
                "llm.generate_questions_failed",
                component="pipeline",
                operation="generate_questions",
                provider_model=model_id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            io.print_session_message(f"LLM question generation failed: {e}", is_warning=True)
            io.print_session_message("Continuing with seed questions only", is_warning=True)
            filtered_questions = []

        all_qs = seed_questions + filtered_questions
        random.shuffle(all_qs)

        session.questions = all_qs
        session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

    io.print_interview_header("simple", len(all_qs) - len(session.answers))

    for i, q in enumerate(all_qs, len(session.answers) + 1):
        # Update context for current question
        session_manager.state_manager.transition_to(
            session,
            ConversationState.WAITING_FOR_INPUT,
            {"current_question_index": i - 1},
        )

        conductor.present_question(q, i, len(all_qs))
        answer_text = conductor.collect_user_input()

        # Check for exit signal
        if answer_text == EXIT_SIGNAL:
            io.print_exit_message()
            break

        if answer_text:
            session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)
            answer = Answer(question_id=q.id, text=answer_text)
            session.answers.append(answer)
            conductor.log_answer_received(session, q, answer_text)
            session_manager.save_with_error_handling(session)

    session_manager.state_manager.transition_to(session, ConversationState.GENERATING_REQUIREMENTS)
    session_manager.state_manager.create_checkpoint(session, "generate_requirements")

    requirements = generate_requirements(provider, project, session.questions, session.answers, session.id, model_id)
    session.requirements = requirements
    session_manager.mark_session_complete(session)

    return session


def run_conversational_interview(
    project: str,
    model_id: str,
    max_questions: int = 15,
    session_id: str | None = None,
    storage: StorageInterface | None = None,
) -> Session:
    """Run a conversational interview, orchestrating session setup and main interview loop."""
    pipeline = ConversationalInterviewPipeline(project, model_id, storage, session_id)
    session, question_counter = pipeline.setup_session(session_id)
    question_queue = pipeline.prepare_initial_question_queue(session, question_counter)

    pipeline.io.print_interview_header("conversational", 0)

    session = pipeline.run_interview_loop(session, question_queue, question_counter, max_questions)
    return pipeline.finalize_session(session)


class ConversationalInterviewPipeline:
    """Encapsulates the conversational interview pipeline workflow."""

    def __init__(
        self,
        project: str,
        model_id: str,
        storage: StorageInterface | None = None,
        session_id: str | None = None,
    ):
        self.project = project
        self.model_id = model_id
        self.provider = Provider.from_id(model_id)
        self.session_manager = SessionManager(storage)
        self.question_queue_manager = QuestionQueue()
        self.io = RichConsoleIO(session_id=session_id)
        self.conductor = InterviewConductor(self.provider, self.session_manager, self.question_queue_manager, self.io)

        # Initialize specialized services
        self.session_setup = SessionSetupManager(self.session_manager)
        self.question_generation = QuestionGenerationService(
            self.provider, self.session_manager, self.question_queue_manager, model_id
        )
        self.completeness_assessment = CompletenessAssessmentService(
            self.conductor, self.session_manager, self.question_generation, model_id
        )
        self.interview_loop = InterviewLoopManager(
            self.conductor, self.session_manager, self.completeness_assessment, model_id
        )
        self.session_finalization = SessionFinalizationService(
            self.provider, self.session_manager, model_id, project, self.io
        )

        self.session_manager.setup_logging_context()

    def setup_session(self, session_id: str | None) -> tuple[Session, int]:
        """Set up session for interview, either loading existing or creating new."""
        session, question_counter = self.session_setup.setup_session(self.project, session_id, "conversational")

        # If it's a new session, set up initial questions
        if question_counter == 0 and not session.questions:
            self.question_generation.setup_initial_session_questions(session, self.project)

        return session, question_counter

    def prepare_initial_question_queue(self, session: Session, question_counter: int) -> list:
        """Prepare initial question queue based on session state."""
        if question_counter == 0:
            return list(session.questions)

        answered_question_ids = {a.question_id for a in session.answers}
        question_queue = [q for q in session.questions if q.id not in answered_question_ids]

        if session.conversation_complete:
            self._reopen_completed_session(session)

        if not question_queue:
            question_queue = self.question_generation.generate_additional_questions(session)

        return question_queue

    def _reopen_completed_session(self, session: Session) -> None:
        """Reopen a completed session for additional questions."""
        self.io.print_session_message("Reopening completed session for additional questions")
        session.conversation_complete = False
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

    def run_interview_loop(
        self,
        session: Session,
        question_queue: list,
        question_counter: int,
        max_questions: int,
    ) -> Session:
        """Run the main interview loop handling questions and answers."""
        return self.interview_loop.run_interview_loop(session, question_queue, question_counter, max_questions)

    def finalize_session(self, session: Session) -> Session:
        """Generate requirements and finalize the session."""
        return self.session_finalization.finalize_session(session)
