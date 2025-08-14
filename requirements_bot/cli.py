import typer

from requirements_bot.core.document import write_document
from requirements_bot.core.pipeline import run_interview

app = typer.Typer(
    help="Requirements Bot - console assistant for gathering software requirements."
)


@app.command()
def interview(
    project: str = typer.Option(..., prompt=True, help="Project name/title"),
    out: str = typer.Option("requirements.md", help="Output requirements file"),
    model: str = typer.Option("openai:gpt-4o-mini", help="Provider:model identifier"),
):
    """
    Runs an interactive interview in the console and writes a requirements document when done.
    """
    _run(project, out, model)


def _run(project: str, out: str, model: str):
    session = run_interview(project=project, model_id=model)
    path = write_document(session, path=out)
    typer.echo(f"Requirements written to {path}")


if __name__ == "__main__":
    app()
