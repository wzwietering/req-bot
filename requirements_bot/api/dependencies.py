import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.exceptions import InvalidSessionIdException
from requirements_bot.core.models import User
from requirements_bot.core.services import SessionAnswerService, SessionService, SessionSetupManager
from requirements_bot.core.services.session_service import SessionValidationError
from requirements_bot.core.services.user_service import UserService
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.core.storage import DatabaseManager, StorageInterface


class StorageConfigurationError(Exception):
    """Raised when storage is not configured correctly."""

    pass


@lru_cache
def get_storage() -> StorageInterface:
    """Get storage instance (cached)."""
    db_path = os.getenv("REQUIREMENTS_BOT_DB_PATH", "./requirements_bot.db")
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
