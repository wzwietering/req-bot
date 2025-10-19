"""Shared test fixtures for API tests."""

import logging
import os
import threading
import time
import uuid
from pathlib import Path

# Set up test environment variables before any other imports
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-characters-for-testing")
os.environ.setdefault("ENVIRONMENT", "test")
# Use mock provider for tests to avoid API calls
os.environ.setdefault("MODEL_ID", "mock:test-model")

import pytest
from fastapi.testclient import TestClient

from specscribe.api.dependencies import get_current_user_id, get_storage
from specscribe.api.main import app
from specscribe.api.middleware import AuthenticationMiddleware
from specscribe.core.models import UserCreate
from specscribe.core.services.user_service import UserService
from specscribe.core.storage import DatabaseManager

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def validate_test_environment():
    """Validate test environment setup."""
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if not jwt_secret or len(jwt_secret) < 32:
        pytest.fail("JWT_SECRET_KEY must be at least 32 characters for testing")

    # Ensure we're in test mode
    assert os.environ.get("ENVIRONMENT") == "test", "Tests must run in test environment"

    logger.info("Test environment validation passed")


# Global variable to store the test user ID
_test_user_id = None


def get_test_user_id() -> str:
    """Override for get_current_user_id dependency in tests."""
    global _test_user_id
    if _test_user_id is None:
        raise RuntimeError("Test user not created yet")
    return _test_user_id


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary database for testing."""
    # Create unique temporary database file in the current directory (project root)
    db_path = Path(f"test_{int(time.time() * 1000)}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}.db")

    # Set environment variable for the test database
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

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
    if original_db_url is not None:
        os.environ["DATABASE_URL"] = original_db_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

    # Clear cache again to reset for next test
    get_storage.cache_clear()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with isolated database."""
    # Store original dependency overrides to restore later
    original_overrides = app.dependency_overrides.copy()

    # Override the authentication dependency for tests
    app.dependency_overrides[get_current_user_id] = get_test_user_id

    # Remove AuthenticationMiddleware from the app for testing
    # This allows tests to bypass JWT token validation while still testing business logic
    original_middleware = app.user_middleware.copy()
    # Filter out AuthenticationMiddleware

    app.user_middleware = [
        m for m in app.user_middleware if not isinstance(m.cls, type) or m.cls != AuthenticationMiddleware
    ]
    app.middleware_stack = None  # Force rebuild of middleware stack
    app.build_middleware_stack()

    # Create a test user in the database to satisfy foreign key constraints
    global _test_user_id
    db_manager = DatabaseManager(db_path=test_db)
    db_session = db_manager.SessionLocal()
    try:
        user_service = UserService(db_session)
        test_user = UserCreate(
            email="test@example.com", provider="google", provider_id="test-provider-id-123", name="Test User"
        )
        created_user = user_service.create_user(test_user)
        _test_user_id = created_user.id
        db_session.commit()
    finally:
        db_session.close()

    with TestClient(app) as test_client:
        yield test_client

    # Restore original middleware stack and dependency overrides
    app.user_middleware = original_middleware
    app.middleware_stack = None
    app.build_middleware_stack()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)
    _test_user_id = None


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {"project": "Test Project API"}


@pytest.fixture
def sample_answer_data():
    """Sample answer data for testing."""
    return {"answer_text": "This is a test answer for API testing"}
