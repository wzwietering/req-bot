import os
import time
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session as DBSession

from specscribe.api.auth import JWTService, OAuth2Providers, get_jwt_service, get_oauth_providers
from specscribe.api.exceptions import InvalidSessionIdException
from specscribe.api.rate_limiting import (
    crud_rate_limiter,
    retry_requirements_rate_limiter,
    retry_user_rate_limiter,
)
from specscribe.api.services.interview_service import APIInterviewService
from specscribe.core.database_models import UserTable
from specscribe.core.models import User
from specscribe.core.services import (
    AnswerCRUDService,
    QuestionCRUDService,
    SessionAnswerService,
    SessionService,
    SessionSetupManager,
)
from specscribe.core.services.refresh_token_service import RefreshTokenService
from specscribe.core.services.session_cookie_config import SessionCookieConfig
from specscribe.core.services.session_service import SessionValidationError
from specscribe.core.services.usage_tracking_service import UsageTrackingService
from specscribe.core.services.user_service import UserService
from specscribe.core.session_manager import SessionManager
from specscribe.core.storage import DatabaseManager, StorageInterface


class StorageConfigurationError(Exception):
    """Raised when storage is not configured correctly."""

    pass


@lru_cache
def get_storage() -> StorageInterface:
    """Get storage instance (cached)."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./specscribe.db")

    # Parse SQLite URL format: sqlite:///path/to/db.db
    if database_url.startswith("sqlite:///"):
        db_path = database_url[10:]  # Remove sqlite:/// prefix
    elif database_url.startswith("sqlite://"):
        db_path = database_url[9:]  # Remove sqlite:// prefix
    else:
        db_path = database_url

    return DatabaseManager(db_path)


def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    storage = get_storage()
    if isinstance(storage, DatabaseManager):
        return storage
    raise StorageConfigurationError("Storage is not configured as DatabaseManager")


def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    storage = get_storage()
    return SessionManager(storage)


def get_session_setup_manager() -> SessionSetupManager:
    """Get session setup manager instance."""
    session_manager = get_session_manager()
    return SessionSetupManager(session_manager)


def get_session_answer_service() -> SessionAnswerService:
    """Get session answer service instance."""
    storage = get_storage()
    return SessionAnswerService(storage)


def get_session_service() -> SessionService:
    """Get session service instance."""
    storage = get_storage()
    return SessionService(storage)


def get_database_session():
    """Get database session with proper cleanup."""
    db_manager = get_database_manager()
    db_session = db_manager.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def get_current_user(request: Request, db_session: Annotated[DBSession, Depends(get_database_session)]) -> User:
    """Get current authenticated user from request state."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db_session)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


def get_current_user_id(request: Request) -> str:
    """Get current user ID from request state."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def get_validated_session_id(session_id: Annotated[str, Path()]) -> str:
    """Validate and return session ID from path parameter."""
    session_service = get_session_service()
    try:
        return session_service.validate_session_id(session_id)
    except SessionValidationError as e:
        raise InvalidSessionIdException(session_id) from e


def get_oauth_providers_with_db() -> OAuth2Providers:
    """Get OAuth providers with database session factory configured."""
    db_manager = get_database_manager()
    return get_oauth_providers(db_manager.SessionLocal)


def get_refresh_token_service() -> RefreshTokenService:
    """Get refresh token service with database session factory."""
    db_manager = get_database_manager()
    return RefreshTokenService(db_manager.SessionLocal)


def get_jwt_service_with_refresh() -> JWTService:
    """Get JWT service with refresh token support."""
    refresh_service = get_refresh_token_service()
    return get_jwt_service(refresh_service)


def get_session_cookie_config() -> SessionCookieConfig:
    """Get session cookie configuration."""
    return SessionCookieConfig()


def get_api_interview_service() -> APIInterviewService:
    """Get API interview service instance."""
    storage = get_storage()
    model_id = os.getenv("MODEL_ID", "anthropic:claude-3-5-haiku-20241022")
    return APIInterviewService(storage, model_id)


def get_question_crud_service() -> QuestionCRUDService:
    """Get question CRUD service instance."""
    storage = get_storage()
    return QuestionCRUDService(storage)


def get_answer_crud_service() -> AnswerCRUDService:
    """Get answer CRUD service instance."""
    storage = get_storage()
    return AnswerCRUDService(storage)


def check_retry_rate_limit(
    session_id: Annotated[str, Depends(get_validated_session_id)], user_id: Annotated[str, Depends(get_current_user_id)]
) -> None:
    """Check rate limit for retry requirements endpoint.

    Enforces two-level rate limiting:
    1. Per-session: Prevents excessive retries for a single session
    2. Per-user: Prevents bypass by creating multiple sessions

    Raises HTTPException if either rate limit is exceeded.
    """
    # Check per-session rate limit
    session_allowed, session_reset_time = retry_requirements_rate_limiter.is_allowed(session_id)

    if not session_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many retry attempts for this session. Please try again later.",
                "details": [{"type": "rate_limit", "message": f"Rate limit reset at {session_reset_time}"}],
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
            },
            headers={"Retry-After": str(session_reset_time - int(time.time()))},
        )

    # Check per-user rate limit
    user_allowed, user_reset_time = retry_user_rate_limiter.is_allowed(user_id)

    if not user_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many retry attempts across all sessions. Please try again later.",
                "details": [{"type": "rate_limit", "message": f"Rate limit reset at {user_reset_time}"}],
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
            },
            headers={"Retry-After": str(user_reset_time - int(time.time()))},
        )


def check_crud_rate_limit(user_id: Annotated[str, Depends(get_current_user_id)]) -> None:
    """Check rate limit for CRUD operations (create, update, delete).

    Enforces per-user rate limiting to prevent spam and abuse.

    Raises HTTPException if rate limit is exceeded.
    """
    allowed, reset_time = crud_rate_limiter.is_allowed(user_id)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many CRUD operations. Please slow down.",
                "details": [{"type": "rate_limit", "message": f"Rate limit reset at {reset_time}"}],
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
            },
            headers={"Retry-After": str(reset_time - int(time.time()))},
        )


def get_usage_tracking_service() -> UsageTrackingService:
    """Get usage tracking service instance."""
    db_manager = get_database_manager()
    return UsageTrackingService(db_manager)


def enforce_question_quota(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db_session: Annotated[DBSession, Depends(get_database_session)],
) -> None:
    """Check if user has quota available for question generation.

    Raises HTTPException(429) if quota exceeded.
    """
    user = db_session.get(UserTable, user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db_manager = get_database_manager()
    service = UsageTrackingService(db_manager)
    service.check_quota_available(user_id, user.tier)
