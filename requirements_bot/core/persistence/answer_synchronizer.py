from requirements_bot.core.database_models import AnswerTable
from requirements_bot.core.models import Answer, Session


class AnswerSynchronizer:
    """Handles synchronization of answers between session objects and database."""

    def sync_answers(self, session: Session, merged_session, db_session) -> None:
        """Synchronize answers between session and database."""
        existing_answers = {a.question_id: a for a in merged_session.answers}
        current_answer_question_ids = set()

        for answer in session.answers:
            current_answer_question_ids.add(answer.question_id)
            if answer.question_id in existing_answers:
                self._update_existing_answer(
                    existing_answers[answer.question_id], answer
                )
            else:
                self._add_new_answer(answer, session.id, db_session)

        self._remove_orphaned_answers(
            existing_answers, current_answer_question_ids, db_session
        )

    def convert_answers_from_table(self, session_table) -> list[Answer]:
        """Convert database answer records to Answer objects."""
        return [
            Answer(
                question_id=a.question_id,
                text=a.text,
                is_vague=a.is_vague,
                needs_followup=a.needs_followup,
            )
            for a in session_table.answers
        ]

    def _update_existing_answer(self, existing_a, answer: Answer) -> None:
        """Update existing answer with new data."""
        existing_a.text = answer.text
        existing_a.is_vague = answer.is_vague
        existing_a.needs_followup = answer.needs_followup

    def _add_new_answer(self, answer: Answer, session_id: str, db_session) -> None:
        """Add new answer to database."""
        a_table = AnswerTable(
            question_id=answer.question_id,
            text=answer.text,
            is_vague=answer.is_vague,
            needs_followup=answer.needs_followup,
            session_id=session_id,
        )
        db_session.add(a_table)

    def _remove_orphaned_answers(
        self, existing_answers: dict, current_question_ids: set, db_session
    ) -> None:
        """Remove answers that are no longer present in session."""
        for question_id, existing_a in existing_answers.items():
            if question_id not in current_question_ids:
                db_session.delete(existing_a)
