import os
from functools import lru_cache

from requirements_bot.core.services import SessionAnswerService, SessionSetupManager
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
