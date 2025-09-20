import typer
from requirements_bot.core.constants import DEFAULT_DB_PATH
from requirements_bot.core.storage import DatabaseManager
from requirements_bot.core.document import write_document
from requirements_bot.core.pipeline import run_interview, run_conversational_interview
from requirements_bot.core.models import Session


class InterviewRunner:
    """Handles the common patterns for running interviews from CLI."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def setup_project_and_session(
        self, project: str | None, session_id: str | None
    ) -> tuple[str, DatabaseManager]:
        """Set up project name and database manager for interview."""
        db_manager = DatabaseManager(self.db_path)

        # If resuming a session, get project from the session
        if session_id and not project:
            existing_session = db_manager.load_session(session_id)
            if existing_session:
                project = existing_session.project
            else:
                typer.echo(f"Session {session_id} not found.", err=True)
                raise typer.Exit(1)

        # If no project provided and not resuming, prompt for it
        if not project:
            project = typer.prompt("Project name/title")

        return project, db_manager

    def finalize_session(self, session: Session, out: str) -> None:
        """Write document and display completion message."""
        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")
        typer.echo(f"Session saved as {session.id}")

    def run_simple_interview(
        self,
        project: str | None,
        out: str,
        model: str,
        session_id: str | None = None,
    ) -> None:
        """Run a simple interview with error handling and fallback."""
        try:
            project, db_manager = self.setup_project_and_session(project, session_id)

            session = run_interview(
                project=project,
                model_id=model,
                session_id=session_id,
                storage=db_manager,
            )
            self.finalize_session(session, out)
        except Exception as e:
            self._handle_fallback(e, project, out, model, "interview")

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
            self._handle_fallback(
                e, project, out, model, "conversational interview", max_questions
            )

    def _handle_fallback(
        self,
        error: Exception,
        project: str | None,
        out: str,
        model: str,
        interview_type: str,
        max_questions: int = None,
    ) -> None:
        """Handle fallback to non-persistent mode."""
        typer.echo(f"Error during {interview_type}: {error}", err=True)
        typer.echo("Falling back to non-persistent mode...")

        if not project:
            project = typer.prompt("Project name/title")

        if interview_type == "conversational interview":
            session = run_conversational_interview(
                project=project, model_id=model, max_questions=max_questions
            )
        else:
            session = run_interview(project=project, model_id=model)

        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")
