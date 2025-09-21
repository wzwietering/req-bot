import os
from functools import lru_cache
from typing import Annotated

from fastapi import Path

from requirements_bot.api.exceptions import InvalidSessionIdException
from requirements_bot.core.services import SessionAnswerService, SessionService, SessionSetupManager
from requirements_bot.core.services.session_service import SessionValidationError
from requirements_bot.core.session_manager import SessionManager
from requirements_bot.core.storage import DatabaseManager, StorageInterface


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
    raise RuntimeError("Storage is not a DatabaseManager instance")


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


def get_validated_session_id(session_id: Annotated[str, Path()]) -> str:
    """Validate and return session ID from path parameter."""
    session_service = get_session_service()
    try:
        return session_service.validate_session_id(session_id)
    except SessionValidationError as e:
        raise InvalidSessionIdException(session_id) from e
