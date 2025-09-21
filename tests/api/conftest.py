"""Shared test fixtures for API tests."""

import logging
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from requirements_bot.api.dependencies import get_storage
from requirements_bot.api.main import app
from requirements_bot.core.storage import DatabaseManager

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary database for testing."""
    # Create unique temporary database file in the current directory (project root)
    import threading
    import time

    db_path = Path(f"test_{int(time.time() * 1000)}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}.db")

    # Set environment variable for the test database
    original_db_path = os.environ.get("REQUIREMENTS_BOT_DB_PATH")
    os.environ["REQUIREMENTS_BOT_DB_PATH"] = str(db_path)

    # Clear the storage cache to ensure fresh instance with new database path
    get_storage.cache_clear()

    # Create database manager to initialize the database
    db_manager = DatabaseManager(db_path=str(db_path))

    yield str(db_path)

    # Cleanup - close all connections first
    try:
        if hasattr(db_manager, "engine") and db_manager.engine:
            db_manager.engine.dispose()
    except Exception as e:
        logger.debug(f"Failed to dispose database engine for {db_path}: {e}")

    # Remove test database file
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception as e:
        logger.debug(f"Failed to delete test database file {db_path}: {e}")

    # Restore original environment variable
    if original_db_path is not None:
        os.environ["REQUIREMENTS_BOT_DB_PATH"] = original_db_path
    elif "REQUIREMENTS_BOT_DB_PATH" in os.environ:
        del os.environ["REQUIREMENTS_BOT_DB_PATH"]

    # Clear cache again to reset for next test
    get_storage.cache_clear()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with isolated database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {"project": "Test Project API"}


@pytest.fixture
def sample_answer_data():
    """Sample answer data for testing."""
    return {"answer_text": "This is a test answer for API testing"}
