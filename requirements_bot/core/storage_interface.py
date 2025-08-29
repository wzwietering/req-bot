from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .models import Session


class StorageInterface(ABC):
    """Abstract interface for session storage implementations."""

    @abstractmethod
    def save_session(self, session: Session) -> str:
        """Save a session to storage. Returns session ID."""
        pass

    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from storage."""
        pass

    @abstractmethod
    def list_sessions(self) -> list[tuple[str, str, datetime, bool]]:
        """List all sessions. Returns (id, project, updated_at, conversation_complete)."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from storage. Returns True if deleted, False if not found."""
        pass
