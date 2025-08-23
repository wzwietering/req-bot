import typer

from requirements_bot.core.document import write_document
from requirements_bot.core.pipeline import run_conversational_interview, run_interview

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
):
    """
    Runs an interactive interview in the console and writes a requirements document when done.
    """
    _run(project, out, model)


@app.command()
def conversational(
    project: str = typer.Option(..., prompt=True, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option(
        "anthropic:claude-3-haiku-20240307", help="Provider:model identifier"
    ),
    max_questions: int = typer.Option(25, help="Maximum number of questions to ask"),
):
    """
    Runs a conversational interview with follow-up questions and intelligent stopping.
    """
    _run_conversational(project, out, model, max_questions)


def _run(project: str, out: str, model: str):
    session = run_interview(project=project, model_id=model)
    path = write_document(session, path=out)
    typer.echo(f"Requirements written to {path}")


def _run_conversational(project: str, out: str, model: str, max_questions: int):
    session = run_conversational_interview(
        project=project, model_id=model, max_questions=max_questions
    )
    path = write_document(session, path=out)
    typer.echo(f"Requirements written to {path}")


if __name__ == "__main__":
    app()
