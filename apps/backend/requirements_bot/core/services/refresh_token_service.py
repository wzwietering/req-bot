import hashlib
import logging
import secrets
import threading
from datetime import UTC, datetime, timedelta

from requirements_bot.core.database_models import RefreshTokenTable
from requirements_bot.core.logging import log_event
from requirements_bot.core.services.token_config import TokenConfig


class RefreshTokenService:
    """Thread-safe refresh token service."""

    def __init__(self, db_session_factory, token_config: TokenConfig | None = None):
        self.db_session_factory = db_session_factory
        self._lock = threading.Lock()
        self._token_config = token_config or TokenConfig()

    def _is_token_expired(self, expires_at: datetime) -> bool:
        """Check if token is expired with clock skew tolerance."""
        now = datetime.now(UTC)
        # Ensure expires_at is timezone-aware (SQLite may return naive datetimes)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        # Consider token expired if it expired more than clock_skew_seconds ago
        return expires_at < (now - timedelta(seconds=self._token_config.clock_skew_seconds))

    def create_refresh_token(self, user_id: str, expire_days: int | None = None) -> str:
        """Create a new refresh token for user."""
        if expire_days is None:
            expire_days = self._token_config.refresh_token_expire_days
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        expires_at = datetime.now(UTC) + timedelta(days=expire_days)

        with self._lock:
            with self.db_session_factory() as db:
                try:
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
                except Exception:
                    db.rollback()
                    raise

    def verify_refresh_token(self, token: str) -> str | None:
        """Verify refresh token and return user_id if valid."""
        if not token:
            return None

        token_hash = self._hash_token(token)

        with self._lock:
            with self.db_session_factory() as db:
                try:
                    refresh_token = (
                        db.query(RefreshTokenTable)
                        .filter(
                            RefreshTokenTable.token_hash == token_hash,
                            RefreshTokenTable.revoked == False,  # noqa: E712
                        )
                        .first()
                    )

                    if refresh_token and not self._is_token_expired(refresh_token.expires_at):
                        return refresh_token.user_id
                    return None
                except Exception as e:
                    log_event(
                        "refresh_token.verify_error",
                        level=logging.ERROR,
                        component="refresh_token",
                        operation="verify_refresh_token",
                        error_type=type(e).__name__,
                        error_msg=str(e),
                    )
                    db.rollback()
                    return None

    def refresh_and_rotate(self, old_token: str, expire_days: int | None = None) -> tuple[str, str] | None:
        """Verify old token, revoke it, and issue new token (token rotation).

        Returns:
            Tuple of (user_id, new_token) if successful, None otherwise
        """
        if not old_token:
            return None

        if expire_days is None:
            expire_days = self._token_config.refresh_token_expire_days

        old_token_hash = self._hash_token(old_token)

        with self._lock:
            with self.db_session_factory() as db:
                try:
                    # Find and validate old token
                    old_refresh_token = (
                        db.query(RefreshTokenTable)
                        .filter(
                            RefreshTokenTable.token_hash == old_token_hash,
                            RefreshTokenTable.revoked == False,  # noqa: E712
                        )
                        .first()
                    )

                    if not old_refresh_token or self._is_token_expired(old_refresh_token.expires_at):
                        return None

                    user_id = old_refresh_token.user_id

                    # Revoke old token
                    old_refresh_token.revoked = True

                    # Create new token
                    new_token = secrets.token_urlsafe(32)
                    new_token_hash = self._hash_token(new_token)
                    expires_at = datetime.now(UTC) + timedelta(days=expire_days)

                    new_refresh_token = RefreshTokenTable(
                        user_id=user_id,
                        token_hash=new_token_hash,
                        created_at=datetime.now(UTC),
                        expires_at=expires_at,
                        revoked=False,
                    )

                    db.add(new_refresh_token)
                    db.commit()

                    return (user_id, new_token)
                except Exception:
                    db.rollback()
                    return None

    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        if not token:
            return False

        token_hash = self._hash_token(token)

        with self._lock:
            with self.db_session_factory() as db:
                try:
                    refresh_token = (
                        db.query(RefreshTokenTable).filter(RefreshTokenTable.token_hash == token_hash).first()
                    )

                    if refresh_token:
                        refresh_token.revoked = True
                        db.commit()
                        return True
                    return False
                except Exception:
                    db.rollback()
                    return False

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user. Returns count of revoked tokens."""
        with self._lock:
            with self.db_session_factory() as db:
                try:
                    tokens = (
                        db.query(RefreshTokenTable)
                        .filter(RefreshTokenTable.user_id == user_id, RefreshTokenTable.revoked == False)  # noqa: E712
                        .all()
                    )

                    count = len(tokens)
                    for token in tokens:
                        token.revoked = True

                    db.commit()
                    return count
                except Exception:
                    db.rollback()
                    return 0

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens. Returns number of cleaned up tokens."""
        with self._lock:
            with self.db_session_factory() as db:
                try:
                    # Use clock skew tolerance when cleaning up expired tokens
                    expiry_threshold = datetime.now(UTC) - timedelta(seconds=self._token_config.clock_skew_seconds)
                    expired_tokens = (
                        db.query(RefreshTokenTable).filter(RefreshTokenTable.expires_at < expiry_threshold).all()
                    )

                    count = len(expired_tokens)
                    for token in expired_tokens:
                        db.delete(token)

                    db.commit()
                    return count
                except Exception:
                    db.rollback()
                    return 0

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
