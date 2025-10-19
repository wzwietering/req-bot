import typer

from specscribe.core.constants import DEFAULT_DB_PATH
from specscribe.core.io_interface import RichConsoleIO
from specscribe.core.models import Session
from specscribe.core.pipeline import run_conversational_interview
from specscribe.core.services import SessionService
from specscribe.core.services.session_service import SessionValidationError
from specscribe.core.storage import DatabaseManager


class InterviewRunner:
    """Handles the common patterns for running interviews from CLI."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.session_service = SessionService(self.db_manager)
        self.io = RichConsoleIO()

    def setup_project_and_session(self, project: str | None, session_id: str | None) -> tuple[str, DatabaseManager]:
        """Set up project name and database manager for interview."""
        try:
            project, session = self.session_service.setup_project_and_session(project, session_id, self.io)
            return project, self.db_manager
        except SessionValidationError as e:
            self.session_service.handle_session_error(e, self.io, exit_on_error=False)
            raise typer.Exit(1)

    def finalize_session(self, session: Session, out: str) -> None:
        """Write document and display completion message."""
        self.session_service.finalize_session_with_document(session, out, self.io)

    def run_conversational_interview_with_fallback(
        self,
        project: str | None,
        out: str,
        model: str,
        max_questions: int,
        session_id: str | None = None,
    ) -> None:
        """Run a conversational interview with error handling and fallback."""
        try:
            project, db_manager = self.setup_project_and_session(project, session_id)

            session = run_conversational_interview(
                project=project,
                model_id=model,
                max_questions=max_questions,
                session_id=session_id,
                storage=db_manager,
            )
            self.finalize_session(session, out)
        except Exception as e:
            self._handle_fallback(e, project, out, model, max_questions)

    def _handle_fallback(
        self,
        error: Exception,
        project: str | None,
        out: str,
        model: str,
        max_questions: int,
    ) -> None:
        """Handle fallback to non-persistent mode."""
        typer.echo(f"Error during conversational interview: {error}", err=True)
        typer.echo("Falling back to non-persistent mode...")

        if not project:
            project = self.io.input("Project name/title: ")

        session = run_conversational_interview(project=project, model_id=model, max_questions=max_questions)
        self.session_service.finalize_session_with_document(session, out, self.io)
