# requirements_bot/core/pipeline.py
import random

from requirements_bot.core.models import Answer, Question, Session
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


def run_interview(project: str, model_id: str) -> Session:
    provider = Provider.from_id(model_id)
    # 1) Seed + provider-augmented questions
    questions = [
        Question(id=f"q{i}", category=c, text=t)
        for i, (c, t) in enumerate(CANNED_SEED_QUESTIONS, 1)
    ]
    llm_questions = provider.generate_questions(project, seed_questions=questions)
    all_qs = questions + [
        q for q in llm_questions if q.text not in {x.text for x in questions}
    ]
    random.shuffle(all_qs)

    # 2) Console loop
    answers: list[Answer] = []
    total_questions = len(all_qs)
    print(f"\n=== Starting interview with {total_questions} questions ===")

    for i, q in enumerate(all_qs, 1):
        print(f"\n[{i}/{total_questions}] [{q.category.upper()}] {q.text}")
        a = input("> ").strip()
        if a:
            answers.append(Answer(question_id=q.id, text=a))

    # 3) Consolidate into requirements (LLM structured output)
    requirements = provider.summarize_requirements(
        project, questions=all_qs, answers=answers
    )

    return Session(
        project=project, questions=all_qs, answers=answers, requirements=requirements
    )
