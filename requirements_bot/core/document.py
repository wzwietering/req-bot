from pathlib import Path

from requirements_bot.core.models import Session


def write_document(session: Session, path: str | Path):
    with open(path, "w") as f:
        f.write(session.to_markdown())
