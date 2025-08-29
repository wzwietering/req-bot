import threading
from datetime import UTC, datetime
from typing import Optional

from .models import Session
from .storage_interface import StorageInterface


class MemoryStorage(StorageInterface):
    """In-memory storage implementation for testing and development."""

    def __init__(self):
        """Initialize in-memory storage."""
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def save_session(self, session: Session) -> str:
        """Save a session to memory. Returns session ID."""
        with self._lock:
            session.updated_at = datetime.now(UTC)
            # Deep copy to avoid external mutations
            import copy

            self._sessions[session.id] = copy.deepcopy(session)
            return session.id

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from memory."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Return a deep copy to avoid external mutations
                import copy

                return copy.deepcopy(session)
            return None

    def list_sessions(self) -> list[tuple[str, str, datetime, bool]]:
        """List all sessions. Returns (id, project, updated_at, conversation_complete)."""
        with self._lock:
            return [
                (s.id, s.project, s.updated_at, s.conversation_complete)
                for s in sorted(
                    self._sessions.values(), key=lambda x: x.updated_at, reverse=True
                )
            ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory. Returns True if deleted, False if not found."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
