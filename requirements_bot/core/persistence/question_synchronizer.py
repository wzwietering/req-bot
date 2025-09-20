from requirements_bot.core.database_models import QuestionTable
from requirements_bot.core.models import Question, Session


class QuestionSynchronizer:
    """Handles synchronization of questions between session objects and database."""

    def sync_questions(self, session: Session, merged_session, db_session) -> None:
        """Synchronize questions between session and database."""
        existing_questions = {q.id: q for q in merged_session.questions}
        current_question_ids = set()

        for i, question in enumerate(session.questions):
            current_question_ids.add(question.id)
            if question.id in existing_questions:
                self._update_existing_question(existing_questions[question.id], question, i)
            else:
                self._add_new_question(question, session.id, i, db_session)

        self._remove_orphaned_questions(existing_questions, current_question_ids, db_session)

    def convert_questions_from_table(self, session_table) -> list[Question]:
        """Convert database question records to Question objects."""
        questions_sorted = sorted(session_table.questions, key=lambda q: q.order_index)
        return [
            Question(
                id=q.id,
                text=q.text,
                category=q.category,
                required=q.required,
            )
            for q in questions_sorted
        ]

    def _update_existing_question(self, existing_q, question: Question, order_index: int) -> None:
        """Update existing question with new data."""
        existing_q.text = question.text
        existing_q.category = question.category
        existing_q.required = question.required
        existing_q.order_index = order_index

    def _add_new_question(self, question: Question, session_id: str, order_index: int, db_session) -> None:
        """Add new question to database."""
        q_table = QuestionTable(
            id=question.id,
            text=question.text,
            category=question.category,
            required=question.required,
            session_id=session_id,
            order_index=order_index,
        )
        db_session.add(q_table)

    def _remove_orphaned_questions(self, existing_questions: dict, current_ids: set, db_session) -> None:
        """Remove questions that are no longer present in session."""
        for q_id, existing_q in existing_questions.items():
            if q_id not in current_ids:
                db_session.delete(existing_q)
