import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Optional

import typer

from requirements_bot.core.document import write_document
from requirements_bot.core.logging import (
    init_logging,
    log_event,
    set_run_id,
    set_trace_id,
)
from requirements_bot.core.constants import DEFAULT_DB_PATH
from requirements_bot.core.pipeline import run_conversational_interview, run_interview
from requirements_bot.core.storage import DatabaseManager
from requirements_bot.cli_helpers import InterviewRunner

app = typer.Typer(
    help="Requirements Bot - console assistant for gathering software requirements."
)


def _init_logging_from_cli(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: str = "text",
    log_mask: bool = False,
) -> None:
    init_logging(level=log_level, fmt=log_format, file_path=log_file, mask=log_mask)
    # Fresh run id for each CLI invocation; also set as initial trace id
    _rid = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")[-12:]
    set_run_id(_rid)
    set_trace_id(_rid)
    log_event(
        "cli.start",
        component="cli",
        operation="start",
        log_level=log_level or "INFO",
        log_file=log_file or "stdout",
        log_format=log_format,
        log_mask=log_mask,
    )


@app.command()
def interview(
    project: str | None = typer.Option(None, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option(
        "anthropic:claude-3-haiku-20240307", help="Provider:model identifier"
    ),
    session_id: str | None = typer.Option(
        None, "--session-id", help="Resume existing session by ID"
    ),
    db_path: str = typer.Option(DEFAULT_DB_PATH, help="Database file path"),
    log_level: str | None = typer.Option(None, help="Log level (DEBUG, INFO, ...)"),
    log_file: str | None = typer.Option(None, help="Log file path (default stdout)"),
    log_format: str = typer.Option("text", help="Log format: json|text"),
    log_mask: bool = typer.Option(False, help="Mask sensitive text in logs"),
):
    """
    Runs an interactive interview in the console and writes a requirements document when done.
    """
    _init_logging_from_cli(log_level, log_file, log_format, log_mask)
    _run(project, out, model, session_id, db_path)


@app.command()
def conversational(
    project: str | None = typer.Option(None, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option(
        "anthropic:claude-3-haiku-20240307", help="Provider:model identifier"
    ),
    max_questions: int = typer.Option(25, help="Maximum number of questions to ask"),
    session_id: str | None = typer.Option(
        None, "--session-id", help="Resume existing session by ID"
    ),
    db_path: str = typer.Option(DEFAULT_DB_PATH, help="Database file path"),
    log_level: str | None = typer.Option(None, help="Log level (DEBUG, INFO, ...)"),
    log_file: str | None = typer.Option(None, help="Log file path (default stdout)"),
    log_format: str = typer.Option("text", help="Log format: json|text"),
    log_mask: bool = typer.Option(False, help="Mask sensitive text in logs"),
):
    """
    Runs a conversational interview with follow-up questions and intelligent stopping.
    """
    _init_logging_from_cli(log_level, log_file, log_format, log_mask)
    _run_conversational(project, out, model, max_questions, session_id, db_path)


@app.command("list-sessions")
def list_sessions(
    db_path: str = typer.Option(DEFAULT_DB_PATH, help="Database file path"),
    log_level: str | None = typer.Option(None, help="Log level (DEBUG, INFO, ...)"),
    log_file: str | None = typer.Option(None, help="Log file path (default stdout)"),
    log_format: str = typer.Option("text", help="Log format: json|text"),
    log_mask: bool = typer.Option(False, help="Mask sensitive text in logs"),
):
    """
    List all stored interview sessions.
    """
    _init_logging_from_cli(log_level, log_file, log_format, log_mask)
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
            typer.echo(f"{session_id} | {project[:30]:<30} | {updated_str} | {status}")

    except Exception as e:
        typer.echo(f"Error listing sessions: {e}", err=True)
        raise typer.Exit(1)


@app.command("delete-session")
def delete_session(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
    db_path: str = typer.Option(DEFAULT_DB_PATH, help="Database file path"),
    log_level: str | None = typer.Option(None, help="Log level (DEBUG, INFO, ...)"),
    log_file: str | None = typer.Option(None, help="Log file path (default stdout)"),
    log_format: str = typer.Option("text", help="Log format: json|text"),
    log_mask: bool = typer.Option(False, help="Mask sensitive text in logs"),
):
    """
    Delete a stored session.
    """
    _init_logging_from_cli(log_level, log_file, log_format, log_mask)
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
    db_path: str = typer.Option(DEFAULT_DB_PATH, help="Database file path"),
    log_level: str | None = typer.Option(None, help="Log level (DEBUG, INFO, ...)"),
    log_file: str | None = typer.Option(None, help="Log file path (default stdout)"),
    log_format: str = typer.Option("text", help="Log format: json|text"),
    log_mask: bool = typer.Option(False, help="Mask sensitive text in logs"),
):
    """
    Display session details and export to markdown.
    """
    _init_logging_from_cli(log_level, log_file, log_format, log_mask)
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
    project: str | None,
    out: str,
    model: str,
    session_id: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
):
    runner = InterviewRunner(db_path)
    runner.run_simple_interview(project, out, model, session_id)


def _run_conversational(
    project: str | None,
    out: str,
    model: str,
    max_questions: int,
    session_id: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
):
    runner = InterviewRunner(db_path)
    runner.run_conversational_interview_with_fallback(
        project, out, model, max_questions, session_id
    )


@app.command("logs-report")
def logs_report(
    input: str = typer.Option(..., "--input", help="Path to JSONL log file"),
    top: int = typer.Option(20, help="Show top N slow operations"),
):
    """
    Generate a simple performance report from JSON logs produced with --log-format json.
    """
    path = Path(input)
    if not path.exists():
        typer.echo(f"Log file not found: {path}", err=True)
        raise typer.Exit(1)

    groups: dict[str, list[float]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            dur = rec.get("duration_ms")
            if dur is None:
                continue
            key = None
            if rec.get("component") and rec.get("operation"):
                key = f"{rec['component']}.{rec['operation']}"
            elif rec.get("event"):
                key = rec["event"]
            else:
                key = "unknown"
            groups.setdefault(key, []).append(float(dur))

    if not groups:
        typer.echo("No span durations found in log.")
        return

    # Prepare rows sorted by max duration
    rows: list[tuple[str, int, float, float, float]] = []
    for key, durations in groups.items():
        durations.sort()
        count = len(durations)
        avg = mean(durations)
        p95 = durations[int(0.95 * (count - 1))] if count > 1 else durations[0]
        rows.append((key, count, avg, p95, durations[-1]))

    rows.sort(key=lambda r: r[4], reverse=True)
    typer.echo("Operation | count | avg_ms | p95_ms | max_ms")
    typer.echo("-" * 70)
    for key, count, avg, p95, mx in rows[:top]:
        typer.echo(f"{key:35} | {count:5d} | {avg:7.2f} | {p95:7.2f} | {mx:7.2f}")


if __name__ == "__main__":
    app()
