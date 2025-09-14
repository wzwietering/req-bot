import logging
import random

from requirements_bot.core.conversation_state import ConversationState

# Configuration constants
MAX_ADDITIONAL_QUESTIONS = 5
MAX_INITIAL_QUESTIONS = 3
MAX_MISSING_AREA_QUESTIONS = 3

from requirements_bot.core.interview.interview_conductor import InterviewConductor
from requirements_bot.core.interview.question_queue import QuestionQueue
from requirements_bot.core.interview.utils import (
    generate_requirements,
    print_interview_header,
    print_requirements_generation,
)
from requirements_bot.core.logging import log_event, span
from requirements_bot.core.models import Answer, Session
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
    conductor = InterviewConductor(provider, session_manager, question_queue)

    session_manager.setup_logging_context()

    session: Session | None = None
    if session_id:
        session = session_manager.load_existing_session(session_id, "simple")

    if session:
        # Transition to waiting for input state if resuming
        session_manager.state_manager.transition_to(
            session, ConversationState.WAITING_FOR_INPUT
        )
        answered_question_ids = {a.question_id for a in session.answers}
        all_qs = [q for q in session.questions if q.id not in answered_question_ids]
    else:
        if session_id:
            print(f"\n⚠ Session {session_id} not found, starting new interview")

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
                llm_questions = provider.generate_questions(
                    project, seed_questions=seed_questions
                )
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
            print(f"⚠ LLM question generation failed: {e}")
            print("⚠ Continuing with seed questions only")
            filtered_questions = []

        all_qs = seed_questions + filtered_questions
        random.shuffle(all_qs)

        session.questions = all_qs
        session_manager.state_manager.transition_to(
            session, ConversationState.WAITING_FOR_INPUT
        )

    print_interview_header("simple", len(all_qs) - len(session.answers))

    for i, q in enumerate(all_qs, len(session.answers) + 1):
        # Update context for current question
        session_manager.state_manager.transition_to(
            session,
            ConversationState.WAITING_FOR_INPUT,
            {"current_question_index": i - 1},
        )

        conductor.present_question(q, i, len(all_qs))
        answer_text = conductor.collect_user_input()

        if answer_text:
            session_manager.state_manager.transition_to(
                session, ConversationState.PROCESSING_ANSWER
            )
            answer = Answer(question_id=q.id, text=answer_text)
            session.answers.append(answer)
            conductor.log_answer_received(session, q, answer_text)
            session_manager.save_with_error_handling(session)

    session_manager.state_manager.transition_to(
        session, ConversationState.GENERATING_REQUIREMENTS
    )
    session_manager.state_manager.create_checkpoint(session, "generate_requirements")

    requirements = generate_requirements(
        provider, project, session.questions, session.answers, session.id, model_id
    )
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
    pipeline = ConversationalInterviewPipeline(project, model_id, storage)
    session, question_counter = pipeline.setup_session(session_id)
    question_queue = pipeline.prepare_initial_question_queue(session, question_counter)

    print_interview_header("conversational", 0)

    session = pipeline.run_interview_loop(
        session, question_queue, question_counter, max_questions
    )
    return pipeline.finalize_session(session)


class ConversationalInterviewPipeline:
    """Encapsulates the conversational interview pipeline workflow."""

    def __init__(
        self, project: str, model_id: str, storage: StorageInterface | None = None
    ):
        self.project = project
        self.model_id = model_id
        self.provider = Provider.from_id(model_id)
        self.session_manager = SessionManager(storage)
        self.question_queue_manager = QuestionQueue()
        self.conductor = InterviewConductor(
            self.provider, self.session_manager, self.question_queue_manager
        )
        self.session_manager.setup_logging_context()

    def setup_session(self, session_id: str | None) -> tuple[Session, int]:
        """Set up session for interview, either loading existing or creating new."""
        session = None
        if session_id:
            session = self.session_manager.load_existing_session(
                session_id, "conversational"
            )

        if session:
            return session, len(session.answers)
        else:
            if session_id:
                print(f"\n⚠ Session {session_id} not found, starting new interview")
            return self._create_new_session(), 0

    def _create_new_session(self) -> Session:
        """Create new session with initial questions."""
        session = self.session_manager.create_new_session(
            self.project, [], "conversational"
        )
        self.session_manager.state_manager.create_checkpoint(
            session, "generate_initial_questions"
        )

        seed_questions = self.question_queue_manager.initialize_from_seeds(
            shuffled=True
        )
        try:
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=self.model_id,
                seed_count=len(seed_questions),
            ):
                llm_questions = self.provider.generate_questions(
                    self.project, seed_questions=seed_questions
                )
        except Exception as e:
            # If LLM question generation fails, log the error and continue with just seed questions
            log_event(
                "llm.generate_questions_failed",
                component="pipeline",
                operation="generate_questions",
                provider_model=self.model_id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            print(f"⚠ LLM question generation failed: {e}")
            print("⚠ Continuing with seed questions only")
            llm_questions = []

        session.questions = seed_questions + llm_questions[:MAX_INITIAL_QUESTIONS]
        self.session_manager.state_manager.transition_to(
            session, ConversationState.WAITING_FOR_INPUT
        )
        return session

    def prepare_initial_question_queue(
        self, session: Session, question_counter: int
    ) -> list:
        """Prepare initial question queue based on session state."""
        if question_counter == 0:
            return list(session.questions)

        answered_question_ids = {a.question_id for a in session.answers}
        question_queue = [
            q for q in session.questions if q.id not in answered_question_ids
        ]

        if session.conversation_complete:
            self._reopen_completed_session(session)

        if not question_queue:
            question_queue = self._generate_additional_questions(session)

        return question_queue

    def _reopen_completed_session(self, session: Session) -> None:
        """Reopen a completed session for additional questions."""
        print("   → Reopening completed session for additional questions")
        session.conversation_complete = False
        self.session_manager.state_manager.transition_to(
            session, ConversationState.WAITING_FOR_INPUT
        )

    def _generate_additional_questions(self, session: Session) -> list:
        """Generate additional questions when queue is empty."""
        print("   → Generating new questions to continue the conversation")
        self.session_manager.state_manager.transition_to(
            session, ConversationState.GENERATING_QUESTIONS
        )
        self.session_manager.state_manager.create_checkpoint(
            session, "generate_additional_questions"
        )

        seed_questions = self.question_queue_manager.initialize_from_seeds(
            shuffled=False
        )
        try:
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=self.model_id,
                seed_count=len(seed_questions),
            ):
                additional_questions = self.provider.generate_questions(
                    session.project, seed_questions=seed_questions
                )
        except Exception as e:
            # If LLM question generation fails, log the error and return empty question queue
            log_event(
                "llm.generate_questions_failed",
                component="pipeline",
                operation="generate_additional_questions",
                provider_model=self.model_id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            print(f"⚠ LLM question generation failed: {e}")
            print("⚠ Unable to generate additional questions")
            additional_questions = []

        new_questions = self.question_queue_manager.filter_asked_questions(
            additional_questions, session
        )
        question_queue = new_questions[:MAX_ADDITIONAL_QUESTIONS]
        self.session_manager.state_manager.transition_to(
            session, ConversationState.WAITING_FOR_INPUT
        )
        return question_queue

    def run_interview_loop(
        self,
        session: Session,
        question_queue: list,
        question_counter: int,
        max_questions: int,
    ) -> Session:
        """Run the main interview loop handling questions and answers."""
        while (
            question_queue
            and question_counter < max_questions
            and not session.conversation_complete
        ):
            current_question = question_queue.pop(0)
            question_counter += 1
            session.questions.append(current_question)

            self.conductor.present_question(
                current_question, question_counter, max_questions
            )
            answer_text = self.conductor.collect_user_input()

            if answer_text:
                self.session_manager.state_manager.transition_to(
                    session, ConversationState.PROCESSING_ANSWER
                )
                question_queue = self._process_answer(
                    session, current_question, answer_text, question_queue
                )

            if self._should_check_completeness(question_counter, len(question_queue)):
                question_queue = self._assess_and_handle_completeness(
                    session, question_queue
                )
                if session.conversation_complete:
                    break

        return session

    def _process_answer(
        self, session: Session, current_question, answer_text: str, question_queue: list
    ) -> list:
        """Process a user's answer and handle follow-ups."""
        # State transition handled by caller - we're already in PROCESSING_ANSWER state
        answer = Answer(question_id=current_question.id, text=answer_text)
        session.answers.append(answer)
        self.conductor.log_answer_received(session, current_question, answer_text)
        self.session_manager.save_with_error_handling(session)

        analysis = self.conductor.analyze_response(
            current_question, answer, session, self.model_id
        )
        self.conductor.update_answer_metadata(answer, analysis)

        if analysis.follow_up_questions:
            self.session_manager.state_manager.transition_to(
                session, ConversationState.GENERATING_FOLLOWUPS
            )
            self.session_manager.state_manager.create_checkpoint(
                session, "generate_followups"
            )

            question_queue = self.conductor.process_followups(
                analysis, current_question, session, question_queue
            )

            self.session_manager.save_with_error_handling(session)

            # Transition back to waiting for input after generating follow-ups
            self.session_manager.state_manager.transition_to(
                session, ConversationState.WAITING_FOR_INPUT
            )
        else:
            # No follow-ups, process normally and continue to waiting
            question_queue = self.conductor.process_followups(
                analysis, current_question, session, question_queue
            )

            self.session_manager.state_manager.transition_to(
                session, ConversationState.WAITING_FOR_INPUT
            )

        return question_queue

    def _should_check_completeness(
        self, question_counter: int, queue_length: int
    ) -> bool:
        """Determine if we should check interview completeness."""
        return self.conductor.should_check_completeness(question_counter, queue_length)

    def _assess_and_handle_completeness(
        self, session: Session, question_queue: list
    ) -> list:
        """Assess interview completeness and handle the result."""
        self.session_manager.state_manager.transition_to(
            session, ConversationState.ASSESSING_COMPLETENESS
        )
        self.session_manager.state_manager.create_checkpoint(
            session, "assess_completeness"
        )

        completeness = self.conductor.assess_interview_status(session, self.model_id)

        if completeness.is_complete:
            self.conductor.handle_completion(completeness)
            session.conversation_complete = True
        else:
            self.conductor.handle_missing_areas(completeness)
            if len(question_queue) == 0:
                question_queue = self._generate_missing_area_questions(session)
            self.session_manager.state_manager.transition_to(
                session, ConversationState.WAITING_FOR_INPUT
            )

        return question_queue

    def _generate_missing_area_questions(self, session: Session) -> list:
        """Generate questions for missing areas identified during completeness assessment."""
        print("   → Generating additional questions for missing areas")
        self.session_manager.state_manager.transition_to(
            session, ConversationState.GENERATING_QUESTIONS
        )
        self.session_manager.state_manager.create_checkpoint(
            session, "generate_missing_area_questions"
        )

        seed_questions = self.question_queue_manager.initialize_from_seeds(
            shuffled=False
        )
        try:
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=self.model_id,
                seed_count=len(seed_questions),
            ):
                additional_questions = self.provider.generate_questions(
                    session.project, seed_questions=seed_questions
                )
        except Exception as e:
            # If LLM question generation fails, log the error and return empty question list
            log_event(
                "llm.generate_questions_failed",
                component="pipeline",
                operation="generate_missing_area_questions",
                provider_model=self.model_id,
                error=str(e),
                error_type=type(e).__name__,
                level=logging.WARNING,
            )
            print(f"⚠ LLM question generation failed: {e}")
            print("⚠ Unable to generate questions for missing areas")
            additional_questions = []

        new_questions = self.question_queue_manager.filter_asked_questions(
            additional_questions, session
        )
        return new_questions[:MAX_MISSING_AREA_QUESTIONS]

    def finalize_session(self, session: Session) -> Session:
        """Generate requirements and finalize the session."""
        print_requirements_generation(len(session.answers))
        self.session_manager.state_manager.transition_to(
            session, ConversationState.GENERATING_REQUIREMENTS
        )
        self.session_manager.state_manager.create_checkpoint(
            session, "generate_final_requirements"
        )

        requirements = generate_requirements(
            self.provider,
            self.project,
            session.questions,
            session.answers,
            session.id,
            self.model_id,
        )
        session.requirements = requirements
        self.session_manager.mark_session_complete(session)
        return session
