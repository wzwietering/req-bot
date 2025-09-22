import hashlib
import secrets
import threading
from datetime import UTC, datetime, timedelta

from requirements_bot.core.database_models import RefreshTokenTable


class RefreshTokenService:
    """Thread-safe refresh token service."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._lock = threading.Lock()

    def create_refresh_token(self, user_id: str, expire_days: int = 30) -> str:
        """Create a new refresh token for user."""
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        expires_at = datetime.now(UTC) + timedelta(days=expire_days)

        with self._lock:
            with self.db_session_factory() as db:
                refresh_token = RefreshTokenTable(
                    user_id=user_id,
                    token_hash=token_hash,
                    created_at=datetime.now(UTC),
                    expires_at=expires_at,
                    revoked=False,
                )
                db.add(refresh_token)
                db.commit()

        return token

    def verify_refresh_token(self, token: str) -> str | None:
        """Verify refresh token and return user_id if valid."""
        if not token:
            return None

        token_hash = self._hash_token(token)

        with self._lock:
            with self.db_session_factory() as db:
                refresh_token = (
                    db.query(RefreshTokenTable)
                    .filter(
                        RefreshTokenTable.token_hash == token_hash,
                        not RefreshTokenTable.revoked,
                        RefreshTokenTable.expires_at > datetime.now(UTC),
                    )
                    .first()
                )

                if refresh_token:
                    return refresh_token.user_id
                return None

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        if not token:
            return False

        token_hash = self._hash_token(token)

        with self._lock:
            with self.db_session_factory() as db:
                refresh_token = db.query(RefreshTokenTable).filter(RefreshTokenTable.token_hash == token_hash).first()

                if refresh_token:
                    refresh_token.revoked = True
                    db.commit()
                    return True
                return False

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user. Returns count of revoked tokens."""
        with self._lock:
            with self.db_session_factory() as db:
                tokens = (
                    db.query(RefreshTokenTable)
                    .filter(RefreshTokenTable.user_id == user_id, not RefreshTokenTable.revoked)
                    .all()
                )

                count = len(tokens)
                for token in tokens:
                    token.revoked = True

                db.commit()
                return count

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens. Returns number of cleaned up tokens."""
        with self._lock:
            with self.db_session_factory() as db:
                expired_tokens = (
                    db.query(RefreshTokenTable).filter(RefreshTokenTable.expires_at < datetime.now(UTC)).all()
                )

                count = len(expired_tokens)
                for token in expired_tokens:
                    db.delete(token)

                db.commit()
                return count

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
