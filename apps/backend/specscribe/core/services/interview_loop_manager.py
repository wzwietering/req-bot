from specscribe.core.conversation_state import ConversationState
from specscribe.core.interview.interview_conductor import InterviewConductor
from specscribe.core.interview_constants import EXIT_SIGNAL
from specscribe.core.models import Answer, Question, Session
from specscribe.core.services.completeness_assessment_service import (
    CompletenessAssessmentService,
)
from specscribe.core.services.question_generation_service import QuestionGenerationService
from specscribe.core.session_manager import SessionManager


class InterviewLoopManager:
    """Manages the main interview loop and answer processing with just-in-time question generation."""

    def __init__(
        self,
        conductor: InterviewConductor,
        session_manager: SessionManager,
        completeness_service: CompletenessAssessmentService,
        question_generation_service: QuestionGenerationService,
        model_id: str,
    ):
        self.conductor = conductor
        self.session_manager = session_manager
        self.completeness_service = completeness_service
        self.question_generation_service = question_generation_service
        self.model_id = model_id

    def run_interview_loop(
        self,
        session: Session,
        question_queue: list[Question],
        question_counter: int,
        max_questions: int,
    ) -> Session:
        """Run the main interview loop handling questions and answers."""
        while self._should_continue_interview(question_queue, question_counter, max_questions, session):
            current_question = question_queue.pop(0)
            question_counter += 1
            session.questions.append(current_question)

            self.conductor.present_question(current_question, question_counter, max_questions)
            answer_text = self.conductor.collect_user_input()

            # Check for exit signal
            if answer_text == EXIT_SIGNAL:
                print("Exiting interview. Session has been saved.")
                return session

            if answer_text:
                self.session_manager.state_manager.transition_to(session, ConversationState.PROCESSING_ANSWER)
                question_queue, should_check_completeness = self._process_answer(
                    session, current_question, answer_text, question_queue
                )

                # Check completeness while still in PROCESSING_ANSWER state (if appropriate)
                if should_check_completeness and self.completeness_service.should_check_completeness(
                    question_counter, len(question_queue)
                ):
                    question_queue = self.completeness_service.assess_and_handle_completeness(session, question_queue)
                    if session.conversation_complete:
                        break
                elif should_check_completeness:
                    # No completeness check needed, transition to waiting state
                    self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)

        return session

    def _should_continue_interview(
        self,
        question_queue: list,
        question_counter: int,
        max_questions: int,
        session: Session,
    ) -> bool:
        """Determine if interview should continue."""
        return bool(question_queue) and question_counter < max_questions and not session.conversation_complete

    def _process_answer(
        self, session: Session, current_question, answer_text: str, question_queue: list
    ) -> tuple[list, bool]:
        """Process a user's answer and handle follow-ups.

        Returns tuple of (question_queue, should_check_completeness).
        """
        answer = Answer(question_id=current_question.id, text=answer_text)
        session.answers.append(answer)
        self.conductor.log_answer_received(session, current_question, answer_text)
        self.session_manager.save_with_error_handling(session)

        analysis = self.conductor.analyze_response(current_question, answer, session, self.model_id)
        self.conductor.update_answer_metadata(answer, analysis)

        if analysis.follow_up_questions:
            self._handle_follow_up_questions(session, analysis, current_question, question_queue)
            return question_queue, False
        else:
            question_queue = self.conductor.process_followups(analysis, current_question, session, question_queue)

            # Just-in-time generation: Check if we need to generate next question
            self._generate_next_question_if_needed(session, question_queue)

            return question_queue, True

    def _generate_next_question_if_needed(self, session: Session, question_queue: list) -> None:
        """Generate next question if queue is running low."""
        new_question = self.question_generation_service.generate_next_question_if_needed(session)
        if new_question:
            question_queue.append(new_question)

    def _handle_follow_up_questions(self, session: Session, analysis, current_question, question_queue: list) -> list:
        """Handle follow-up questions generation."""
        self.session_manager.state_manager.transition_to(session, ConversationState.GENERATING_FOLLOWUPS)
        self.session_manager.state_manager.create_checkpoint(session, "generate_followups")

        question_queue = self.conductor.process_followups(analysis, current_question, session, question_queue)

        self.session_manager.save_with_error_handling(session)

        # Transition back to waiting for input after generating follow-ups
        self.session_manager.state_manager.transition_to(session, ConversationState.WAITING_FOR_INPUT)
        return question_queue
