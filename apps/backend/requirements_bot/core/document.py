from pathlib import Path

from requirements_bot.core.models import Session


def write_document(session: Session, path: str | Path) -> str:
    """Write session to markdown document and return the path."""
    path_obj = Path(path)
    with open(path_obj, "w") as f:
        f.write(session.to_markdown())
    return str(path_obj.resolve())
