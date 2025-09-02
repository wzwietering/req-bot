import random

from requirements_bot.core.logging import (
    get_run_id,
    get_trace_id,
    log_event,
    set_run_id,
    set_trace_id,
    span,
)
from requirements_bot.core.models import Question, Session
from requirements_bot.core.storage_interface import StorageInterface


class SessionManager:
    def __init__(self, storage: StorageInterface | None = None):
        self.storage = storage

    def setup_logging_context(self) -> None:
        if not get_trace_id():
            rid = get_run_id()
            if not rid:
                rid = f"run-{random.randint(100000, 999999)}"
                set_run_id(rid)
            set_trace_id(rid)

    def load_existing_session(self, session_id: str, mode: str) -> Session | None:
        if not self.storage:
            return None

        session = self.storage.load_session(session_id)
        if session:
            print(f"\n=== Resuming {mode} interview for '{session.project}' ===")
            set_trace_id(session.id)
            log_event(
                "interview.resume",
                component="pipeline",
                operation="resume",
                session_id=session.id,
                project=session.project,
                mode=mode,
            )
        return session

    def create_new_session(
        self, project: str, questions: list[Question], mode: str
    ) -> Session:
        session = Session(
            project=project,
            questions=questions,
            answers=[],
            requirements=[],
            conversation_complete=mode == "interview",
        )
        set_trace_id(session.id)
        log_event(
            "interview.start",
            component="pipeline",
            operation="start",
            session_id=session.id,
            project=project,
            mode=mode,
        )
        return session

    def save_with_error_handling(
        self, session: Session, is_final: bool = False
    ) -> None:
        if not self.storage:
            return

        try:
            with span(
                "db.save_session",
                component="db",
                operation="save_session",
                session_id=session.id,
                answers=len(session.answers),
                questions=len(session.questions),
                final=is_final,
            ):
                self.storage.save_session(session)
        except Exception as e:
            warning_type = "final session" if is_final else "session"
            print(f"⚠ Warning: Failed to save {warning_type}: {e}")

    def mark_session_complete(self, session: Session) -> None:
        session.conversation_complete = True
        self.save_with_error_handling(session, is_final=True)
