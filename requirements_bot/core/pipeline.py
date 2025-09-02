import random

from requirements_bot.core.interview_conductor import InterviewConductor
from requirements_bot.core.interview_utils import (
    generate_requirements,
    print_interview_header,
    print_requirements_generation,
)
from requirements_bot.core.logging import span
from requirements_bot.core.models import Answer, Session
from requirements_bot.core.question_queue import QuestionQueue
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
        answered_question_ids = {a.question_id for a in session.answers}
        all_qs = [q for q in session.questions if q.id not in answered_question_ids]
    else:
        if session_id:
            print(f"\n⚠ Session {session_id} not found, starting new interview")

        seed_questions = question_queue.initialize_from_seeds(shuffled=False)
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
        all_qs = seed_questions + filtered_questions
        random.shuffle(all_qs)

        session = session_manager.create_new_session(project, all_qs, "simple")

    print_interview_header("simple", len(all_qs) - len(session.answers))

    for i, q in enumerate(all_qs, len(session.answers) + 1):
        conductor.present_question(q, i, len(all_qs))
        answer_text = conductor.collect_user_input()

        if answer_text:
            answer = Answer(question_id=q.id, text=answer_text)
            session.answers.append(answer)
            conductor.log_answer_received(session, q, answer_text)
            session_manager.save_with_error_handling(session)

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
    provider = Provider.from_id(model_id)
    session_manager = SessionManager(storage)
    question_queue_manager = QuestionQueue()
    conductor = InterviewConductor(provider, session_manager, question_queue_manager)

    session_manager.setup_logging_context()

    session: Session | None = None
    if session_id:
        session = session_manager.load_existing_session(session_id, "simple")

    question_counter = 0

    if session:
        question_counter = len(session.answers)
        answered_question_ids = {a.question_id for a in session.answers}
        question_queue = [
            q for q in session.questions if q.id not in answered_question_ids
        ]

        if session.conversation_complete:
            print("   → Reopening completed session for additional questions")
            session.conversation_complete = False

        if not question_queue:
            print("   → Generating new questions to continue the conversation")
            seed_questions = question_queue_manager.initialize_from_seeds(
                shuffled=False
            )
            with span(
                "llm.generate_questions",
                component="pipeline",
                operation="generate_questions",
                provider_model=model_id,
                seed_count=len(seed_questions),
            ):
                additional_questions = provider.generate_questions(
                    session.project, seed_questions=seed_questions
                )
            new_questions = question_queue_manager.filter_asked_questions(
                additional_questions, session
            )
            question_queue.extend(new_questions[:5])
    else:
        if session_id:
            print(f"\n⚠ Session {session_id} not found, starting new interview")

        seed_questions = question_queue_manager.initialize_from_seeds(shuffled=True)
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
        question_queue = seed_questions + llm_questions[:3]
        session = session_manager.create_new_session(project, [], "conversational")

    print_interview_header("conversational", 0)

    while (
        question_queue
        and question_counter < max_questions
        and not session.conversation_complete
    ):
        current_question = question_queue.pop(0)
        question_counter += 1
        session.questions.append(current_question)

        conductor.present_question(current_question, question_counter, max_questions)
        answer_text = conductor.collect_user_input()

        if answer_text:
            answer = Answer(question_id=current_question.id, text=answer_text)
            session.answers.append(answer)
            conductor.log_answer_received(session, current_question, answer_text)
            session_manager.save_with_error_handling(session)

            analysis = conductor.analyze_response(
                current_question, answer, session, model_id
            )
            conductor.update_answer_metadata(answer, analysis)
            question_queue = conductor.process_followups(
                analysis, current_question, session, question_queue
            )

            if analysis.follow_up_questions:
                session_manager.save_with_error_handling(session)

        if conductor.should_check_completeness(question_counter, len(question_queue)):
            completeness = conductor.assess_interview_status(session, model_id)

            if completeness.is_complete:
                conductor.handle_completion(completeness)
                session.conversation_complete = True
                break
            else:
                conductor.handle_missing_areas(completeness)
                if len(question_queue) == 0:
                    print("   → Generating additional questions for missing areas")
                    seed_questions = question_queue_manager.initialize_from_seeds(
                        shuffled=False
                    )
                    with span(
                        "llm.generate_questions",
                        component="pipeline",
                        operation="generate_questions",
                        provider_model=model_id,
                        seed_count=len(seed_questions),
                    ):
                        additional_questions = provider.generate_questions(
                            session.project, seed_questions=seed_questions
                        )
                    new_questions = question_queue_manager.filter_asked_questions(
                        additional_questions, session
                    )
                    question_queue.extend(new_questions[:3])

    print_requirements_generation(len(session.answers))
    requirements = generate_requirements(
        provider, project, session.questions, session.answers, session.id, model_id
    )
    session.requirements = requirements
    session_manager.mark_session_complete(session)

    return session
