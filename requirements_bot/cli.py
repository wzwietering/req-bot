from datetime import datetime
from typing import Optional

import typer

from requirements_bot.core.document import write_document
from requirements_bot.core.pipeline import run_conversational_interview, run_interview
from requirements_bot.core.storage import DatabaseManager

app = typer.Typer(
    help="Requirements Bot - console assistant for gathering software requirements."
)


@app.command()
def interview(
    project: str = typer.Option(..., prompt=True, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option(
        "anthropic:claude-3-haiku-20240307", help="Provider:model identifier"
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Resume existing session by ID"
    ),
    db_path: str = typer.Option("requirements_bot.db", help="Database file path"),
):
    """
    Runs an interactive interview in the console and writes a requirements document when done.
    """
    _run(project, out, model, session_id, db_path)


@app.command()
def conversational(
    project: str = typer.Option(..., prompt=True, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option(
        "anthropic:claude-3-haiku-20240307", help="Provider:model identifier"
    ),
    max_questions: int = typer.Option(25, help="Maximum number of questions to ask"),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Resume existing session by ID"
    ),
    db_path: str = typer.Option("requirements_bot.db", help="Database file path"),
):
    """
    Runs a conversational interview with follow-up questions and intelligent stopping.
    """
    _run_conversational(project, out, model, max_questions, session_id, db_path)


@app.command("list-sessions")
def list_sessions(
    db_path: str = typer.Option("requirements_bot.db", help="Database file path"),
):
    """
    List all stored interview sessions.
    """
    try:
        db_manager = DatabaseManager(db_path)
        sessions = db_manager.list_sessions()

        if not sessions:
            typer.echo("No sessions found.")
            return

        typer.echo("Stored sessions:")
        typer.echo("-" * 80)

        for session_id, project, updated_at, complete in sessions:
            status = "✓ Complete" if complete else "⚠ In Progress"
            updated_str = updated_at.strftime("%Y-%m-%d %H:%M:%S")
            typer.echo(
                f"{session_id[:8]}... | {project[:30]:<30} | {updated_str} | {status}"
            )

    except Exception as e:
        typer.echo(f"Error listing sessions: {e}", err=True)
        raise typer.Exit(1)


@app.command("delete-session")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    db_path: str = typer.Option("requirements_bot.db", help="Database file path"),
):
    """
    Delete a stored session.
    """
    try:
        db_manager = DatabaseManager(db_path)

        if db_manager.delete_session(session_id):
            typer.echo(f"Session {session_id} deleted successfully.")
        else:
            typer.echo(f"Session {session_id} not found.", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"Error deleting session: {e}", err=True)
        raise typer.Exit(1)


@app.command("show-session")
def show_session(
    session_id: str = typer.Argument(..., help="Session ID to display"),
    db_path: str = typer.Option("requirements_bot.db", help="Database file path"),
):
    """
    Display session details and export to markdown.
    """
    try:
        db_manager = DatabaseManager(db_path)
        session = db_manager.load_session(session_id)

        if not session:
            typer.echo(f"Session {session_id} not found.", err=True)
            raise typer.Exit(1)

        typer.echo(f"Session: {session.id}")
        typer.echo(f"Project: {session.project}")
        typer.echo(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        typer.echo(f"Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        typer.echo(f"Questions: {len(session.questions)}")
        typer.echo(f"Answers: {len(session.answers)}")
        typer.echo(f"Requirements: {len(session.requirements)}")
        typer.echo(f"Complete: {'Yes' if session.conversation_complete else 'No'}")

        export = typer.confirm("Export to markdown file?")
        if export:
            filename = (
                f"{session.project.replace(' ', '_').lower()}_{session_id[:8]}.md"
            )
            path = write_document(session, path=filename)
            typer.echo(f"Exported to {path}")

    except Exception as e:
        typer.echo(f"Error showing session: {e}", err=True)
        raise typer.Exit(1)


def _run(
    project: str,
    out: str,
    model: str,
    session_id: Optional[str] = None,
    db_path: str = "requirements_bot.db",
):
    try:
        db_manager = DatabaseManager(db_path)
        session = run_interview(
            project=project,
            model_id=model,
            session_id=session_id,
            db_manager=db_manager,
        )
        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")
        typer.echo(f"Session saved as {session.id}")
    except Exception as e:
        typer.echo(f"Error during interview: {e}", err=True)
        # Fall back to non-persistent mode
        typer.echo("Falling back to non-persistent mode...")
        session = run_interview(project=project, model_id=model)
        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")


def _run_conversational(
    project: str,
    out: str,
    model: str,
    max_questions: int,
    session_id: Optional[str] = None,
    db_path: str = "requirements_bot.db",
):
    try:
        db_manager = DatabaseManager(db_path)
        session = run_conversational_interview(
            project=project,
            model_id=model,
            max_questions=max_questions,
            session_id=session_id,
            db_manager=db_manager,
        )
        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")
        typer.echo(f"Session saved as {session.id}")
    except Exception as e:
        typer.echo(f"Error during conversational interview: {e}", err=True)
        # Fall back to non-persistent mode
        typer.echo("Falling back to non-persistent mode...")
        session = run_conversational_interview(
            project=project, model_id=model, max_questions=max_questions
        )
        path = write_document(session, path=out)
        typer.echo(f"Requirements written to {path}")


if __name__ == "__main__":
    app()
