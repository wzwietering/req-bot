import secrets
import threading
from datetime import UTC, datetime, timedelta

from requirements_bot.core.database_models import OAuthStateTable


class OAuthStateService:
    """Thread-safe persistent OAuth state storage service."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._lock = threading.Lock()

    def generate_state(self, expire_minutes: int = 5) -> str:
        """Generate and store OAuth state parameter for CSRF protection."""
        state = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(minutes=expire_minutes)

        with self._lock:
            with self.db_session_factory() as db:
                oauth_state = OAuthStateTable(state=state, created_at=datetime.now(UTC), expires_at=expires_at)
                db.add(oauth_state)
                db.commit()

        return state

    def verify_and_consume_state(self, state: str) -> bool:
        """Verify OAuth state parameter and remove it (consume once)."""
        if not state:
            return False

        with self._lock:
            with self.db_session_factory() as db:
                oauth_state = db.query(OAuthStateTable).filter(OAuthStateTable.state == state).first()

                if not oauth_state:
                    return False

                # Check if state is not expired
                if datetime.now(UTC) > oauth_state.expires_at:
                    # Clean up expired state
                    db.delete(oauth_state)
                    db.commit()
                    return False

                # State is valid, consume it
                db.delete(oauth_state)
                db.commit()
                return True

    def cleanup_expired_states(self) -> int:
        """Clean up expired OAuth states. Returns number of cleaned up states."""
        with self._lock:
            with self.db_session_factory() as db:
                expired_states = db.query(OAuthStateTable).filter(OAuthStateTable.expires_at < datetime.now(UTC)).all()

                count = len(expired_states)
                for state in expired_states:
                    db.delete(state)

                db.commit()
                return count
