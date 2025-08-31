import logging
import random

from requirements_bot.core.logging import (
    get_run_id,
    get_trace_id,
    log_event,
    mask_text,
    set_run_id,
    set_trace_id,
    span,
)
from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.storage import DatabaseManager
from requirements_bot.providers.base import Provider

CANNED_SEED_QUESTIONS = [
    ("scope", "What problem are we solving?"),
    ("users", "Who are the primary users and their key jobs?"),
    ("constraints", "What platform, budget, or timeline constraints exist?"),
    ("nonfunctional", "Any performance, security, or compliance needs?"),
    ("interfaces", "What external systems or APIs must we integrate with?"),
    ("data", "What data do we store, and what is the source of truth?"),
    ("risks", "Top 3 risks or unknowns?"),
    ("success", "How will we measure success?"),
]


def run_interview(
    project: str,
    model_id: str,
    session_id: str | None = None,
    db_manager: DatabaseManager | None = None,
) -> Session:
    # Ensure a trace id is available before any spans
    if not get_trace_id():
        rid = get_run_id()
        if not rid:
            rid = f"run-{random.randint(100000, 999999)}"
            set_run_id(rid)
        set_trace_id(rid)

    provider = Provider.from_id(model_id)

    # Check if resuming an existing session
    session = None
    if session_id and db_manager:
        session = db_manager.load_session(session_id)
        if session:
            print(f"\n=== Resuming interview for '{session.project}' ===")
            set_trace_id(session.id)
            log_event(
                "interview.resume",
                component="pipeline",
                operation="resume",
                session_id=session.id,
                project=session.project,
                mode="simple",
            )
            # Continue from where we left off
            answered_question_ids = {a.question_id for a in session.answers}
            remaining_questions = [
                q for q in session.questions if q.id not in answered_question_ids
            ]
            all_qs = remaining_questions
        else:
            print(f"\n⚠ Session {session_id} not found, starting new interview")

    if not session:
        # 1) Seed + provider-augmented questions
        questions = [
            Question(id=f"q{i}", category=c, text=t)
            for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
        ]
        with span(
            "llm.generate_questions",
            component="pipeline",
            operation="generate_questions",
            provider_model=model_id,
            seed_count=len(questions),
        ):
            llm_questions = provider.generate_questions(
                project, seed_questions=questions
            )
        all_qs = questions + [
            q for q in llm_questions if q.text not in {x.text for x in questions}
        ]
        random.shuffle(all_qs)

        session = Session(
            project=project, questions=all_qs, answers=[], requirements=[]
        )
        set_trace_id(session.id)
        log_event(
            "interview.start",
            component="pipeline",
            operation="start",
            session_id=session.id,
            project=project,
            mode="simple",
            total_questions=len(all_qs),
        )

    # 2) Console loop
    total_questions = len(all_qs)
    answered_count = len(session.answers)
    print(
        f"\n=== Starting interview with {total_questions - answered_count} remaining questions ==="
    )

    for i, q in enumerate(all_qs, answered_count + 1):
        print(f"\n[{i}/{total_questions}] [{q.category.upper()}] {q.text}")
        a = input("> ").strip()
        if a:
            answer = Answer(question_id=q.id, text=a)
            session.answers.append(answer)
            log_event(
                "answer.received",
                component="pipeline",
                operation="answer",
                session_id=session.id,
                question_id=q.id,
                category=q.category,
                text_len=len(a),
                preview=mask_text(a)[:80],
            )

            # Auto-save after each answer if db_manager is available
            if db_manager:
                try:
                    with span(
                        "db.save_session",
                        component="db",
                        operation="save_session",
                        session_id=session.id,
                        answers=len(session.answers),
                        questions=len(session.questions),
                    ):
                        db_manager.save_session(session)
                except Exception as e:
                    print(f"⚠ Warning: Failed to save session: {e}")

    # 3) Consolidate into requirements (LLM structured output)
    with span(
        "llm.summarize_requirements",
        component="pipeline",
        operation="summarize_requirements",
        session_id=session.id,
        answers=len(session.answers),
        questions=len(session.questions),
        provider_model=model_id,
    ):
        requirements = provider.summarize_requirements(
            project, session.questions, session.answers
        )
    session.requirements = requirements
    session.conversation_complete = True

    # Final save
    if db_manager:
        try:
            with span(
                "db.save_session",
                component="db",
                operation="save_session",
                session_id=session.id,
                answers=len(session.answers),
                questions=len(session.questions),
                final=True,
            ):
                db_manager.save_session(session)
        except Exception as e:
            print(f"⚠ Warning: Failed to save final session: {e}")

    return session


def run_conversational_interview(
    project: str,
    model_id: str,
    max_questions: int = 15,
    session_id: str | None = None,
    db_manager: DatabaseManager | None = None,
) -> Session:
    """Run an interactive conversational requirements interview."""
    # Ensure a trace id is available before any spans
    if not get_trace_id():
        rid = get_run_id()
        if not rid:
            rid = f"run-{random.randint(100000, 999999)}"
            set_run_id(rid)
        set_trace_id(rid)
    logger = logging.getLogger("requirements_bot")
    provider = Provider.from_id(model_id)

    # Check if resuming an existing session
    session = None
    question_queue: list[Question] = []
    question_counter = 0

    if session_id and db_manager:
        session = db_manager.load_session(session_id)
        if session:
            print(
                f"\n=== Resuming conversational interview for '{session.project}' ==="
            )
            question_counter = len(session.answers)
            set_trace_id(session.id)
            log_event(
                "interview.resume",
                component="pipeline",
                operation="resume",
                session_id=session.id,
                project=session.project,
                mode="conversational",
            )

            # Rebuild question queue from unanswered questions
            answered_question_ids = {a.question_id for a in session.answers}
            remaining_questions = [
                q for q in session.questions if q.id not in answered_question_ids
            ]
            question_queue = remaining_questions

            # If resuming a "completed" session, reopen it for more questions
            if session.conversation_complete:
                print("   → Reopening completed session for additional questions")
                session.conversation_complete = False

            # If no remaining questions, generate new ones to continue the conversation
            if not question_queue:
                print("   → Generating new questions to continue the conversation")
                seed_questions = [
                    Question(id=f"q{i}", category=c, text=t, required=True)
                    for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
                ]
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
                # Filter out questions that are too similar to already asked ones
                asked_texts = {q.text.lower() for q in session.questions}
                new_questions = [
                    q for q in additional_questions if q.text.lower() not in asked_texts
                ]
                question_queue.extend(new_questions[:5])  # Add up to 5 new questions
        else:
            print(f"\n⚠ Session {session_id} not found, starting new interview")

    if not session:
        # Start with seed questions
        seed_questions = [
            Question(id=f"q{i}", category=c, text=t, required=True)
            for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
        ]

        # Get initial LLM-generated questions
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

        session = Session(
            project=project,
            questions=[],  # Will build this dynamically
            answers=[],
            conversation_complete=False,
        )

        # Question queue - start with shuffled seed questions
        question_queue = seed_questions.copy()
        random.shuffle(question_queue)

        # Add some initial LLM questions to the queue
        question_queue.extend(llm_questions[:3])

        question_counter = 0
        set_trace_id(session.id)
        log_event(
            "interview.start",
            component="pipeline",
            operation="start",
            session_id=session.id,
            project=project,
            mode="conversational",
        )

    print(f"\n=== Starting conversational interview ===")
    print(
        "I'll ask questions to understand your requirements. I may ask follow-up questions based on your answers."
    )

    while (
        question_queue
        and question_counter < max_questions
        and not session.conversation_complete
    ):
        current_question: Question = question_queue.pop(0)
        question_counter += 1

        # Add question to session
        session.questions.append(current_question)

        # Ask the question
        print(
            f"\n[{question_counter}] [{current_question.category.upper()}] {current_question.text}"
        )
        answer_text = input("> ").strip()

        if answer_text:
            answer = Answer(question_id=current_question.id, text=answer_text)
            session.answers.append(answer)
            log_event(
                "answer.received",
                component="pipeline",
                operation="answer",
                session_id=session.id,
                question_id=current_question.id,
                category=current_question.category,
                text_len=len(answer_text),
                preview=mask_text(answer_text)[:80],
            )

            # Auto-save after each answer if db_manager is available
            if db_manager:
                try:
                    with span(
                        "db.save_session",
                        component="db",
                        operation="save_session",
                        session_id=session.id,
                        answers=len(session.answers),
                        questions=len(session.questions),
                    ):
                        db_manager.save_session(session)
                except Exception as e:
                    print(f"⚠ Warning: Failed to save session: {e}")

            # Analyze the answer and potentially generate follow-ups
            context = session.get_context_for_question(current_question.id)
            with span(
                "llm.analyze_answer",
                component="pipeline",
                operation="analyze_answer",
                session_id=session.id,
                provider_model=model_id,
                question_id=current_question.id,
                category=current_question.category,
                answer_len=len(answer_text),
            ):
                analysis = provider.analyze_answer(current_question, answer, context)

            # Update answer with analysis results
            answer.is_vague = not (analysis.is_complete and analysis.is_specific)
            answer.needs_followup = bool(analysis.follow_up_questions)

            # Add follow-up questions to the queue
            if analysis.follow_up_questions:
                follow_up_questions: list[Question] = []
                for i, follow_up_text in enumerate(analysis.follow_up_questions):
                    follow_up_id = f"followup_{current_question.id}_{i}"
                    follow_up = Question(
                        id=follow_up_id,
                        text=follow_up_text,
                        category=current_question.category,
                        required=False,
                    )
                    follow_up_questions.append(follow_up)
                    session.questions.append(
                        follow_up
                    )  # Add to session for persistence

                # Insert follow-ups at the front of the queue for immediate asking
                question_queue = follow_up_questions + question_queue

                if analysis.analysis_notes:
                    print(f"   → I need to ask a follow-up: {analysis.analysis_notes}")

                # Save session with new follow-up questions
                if db_manager:
                    try:
                        with span(
                            "db.save_session",
                            component="db",
                            operation="save_session",
                            session_id=session.id,
                            answers=len(session.answers),
                            questions=len(session.questions),
                        ):
                            db_manager.save_session(session)
                    except Exception as e:
                        print(f"⚠ Warning: Failed to save session with follow-ups: {e}")

        # Every few questions, check if we have enough information
        # But don't check completeness too early - need at least 5 questions minimum
        if (question_counter % 5 == 0 and question_counter >= 5) or (
            len(question_queue) == 0 and question_counter >= 5
        ):
            with span(
                "llm.assess_completeness",
                component="pipeline",
                operation="assess_completeness",
                session_id=session.id,
                provider_model=model_id,
                qa_count=len(session.questions),
            ):
                completeness = provider.assess_completeness(session)

            if completeness.is_complete:
                print(f"\n✓ Assessment: {completeness.reasoning}")
                session.conversation_complete = True
                break
            elif completeness.missing_areas:
                print(
                    f"\n⚠ Still need info on: {', '.join(completeness.missing_areas)}"
                )
                # Generate more questions for missing areas if queue is empty
                if len(question_queue) == 0:
                    print("   → Generating additional questions for missing areas")
                    seed_questions = [
                        Question(id=f"q{i}", category=c, text=t, required=True)
                        for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
                    ]
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
                    # Filter out questions that are too similar to already asked ones
                    asked_texts = {q.text.lower() for q in session.questions}
                    new_questions = [
                        q
                        for q in additional_questions
                        if q.text.lower() not in asked_texts
                    ]
                    question_queue.extend(
                        new_questions[:3]
                    )  # Add up to 3 new questions

    # Generate final requirements
    print(f"\n=== Generating requirements from {len(session.answers)} answers ===")
    with span(
        "llm.summarize_requirements",
        component="pipeline",
        operation="summarize_requirements",
        session_id=session.id,
        provider_model=model_id,
        answers=len(session.answers),
        questions=len(session.questions),
    ):
        requirements = provider.summarize_requirements(
            project, session.questions, session.answers
        )
    session.requirements = requirements
    session.conversation_complete = True

    # Final save
    if db_manager:
        try:
            with span(
                "db.save_session",
                component="db",
                operation="save_session",
                session_id=session.id,
                answers=len(session.answers),
                questions=len(session.questions),
                final=True,
            ):
                db_manager.save_session(session)
        except Exception as e:
            print(f"⚠ Warning: Failed to save final session: {e}")

    return session
