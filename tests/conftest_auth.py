"""Extended test configuration for authentication tests."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import existing conftest configuration


@pytest.fixture(scope="session", autouse=True)
def setup_auth_test_environment():
    """Set up authentication-specific test environment."""
    # Set required environment variables for auth tests
    test_env_vars = {
        "JWT_SECRET_KEY": "test-auth-secret-key-with-at-least-32-characters-for-authentication-testing",
        "ENVIRONMENT": "test",
        "OAUTH_ALLOWED_DOMAINS": "localhost,127.0.0.1,testdomain.com",
        "TRUSTED_PROXIES": "",
        "COOKIE_SAMESITE": "lax",
        "COOKIE_MAX_AGE": "3600",
        "COOKIE_DOMAIN": "",
    }

    # Store original values
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is not None:
            os.environ[key] = original_value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def auth_test_config():
    """Authentication test configuration."""
    return {
        "oauth": {
            "providers": ["google", "github", "microsoft"],
            "code_max_length": 512,
            "state_max_length": 128,
            "state_min_length": 10,
            "error_max_length": 256,
        },
        "rate_limiting": {"oauth_requests": 5, "oauth_window": 60, "refresh_requests": 10, "refresh_window": 3600},
        "security": {
            "allowed_domains": ["localhost", "127.0.0.1", "testdomain.com"],
            "secure_cookies_production": True,
            "required_headers": ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"],
        },
    }


@pytest.fixture
def temp_test_files():
    """Create temporary files for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    files = {}

    # Create test files as needed
    files["temp_dir"] = temp_dir

    yield files

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class AuthTestMarkers:
    """Custom test markers for authentication tests."""

    UNIT = "unit"  # Unit tests
    INTEGRATION = "integration"  # Integration tests
    SECURITY = "security"  # Security-focused tests
    SLOW = "slow"  # Slow running tests
    CONCURRENT = "concurrent"  # Concurrency tests


# Register custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    markers = [
        "unit: Unit tests for individual components",
        "integration: Integration tests across components",
        "security: Security-focused tests",
        "slow: Tests that take longer to run",
        "concurrent: Tests involving concurrent operations",
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)


@pytest.fixture
def security_test_environment():
    """Set up environment for security testing."""
    # Temporarily modify security settings for testing
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",  # Test production security
            "OAUTH_ALLOWED_DOMAINS": "secure.example.com",
            "TRUSTED_PROXIES": "192.168.1.1",
            "COOKIE_SAMESITE": "strict",
        },
    ):
        yield


@pytest.fixture
def performance_test_config():
    """Configuration for performance testing."""
    return {
        "max_execution_time": 1.0,  # Maximum execution time in seconds
        "max_memory_usage": 100 * 1024 * 1024,  # 100MB
        "concurrent_requests": 100,
        "stress_test_iterations": 1000,
    }


@pytest.fixture
def mock_external_services():
    """Mock external services for testing."""
    mocks = {}

    # Mock OAuth provider APIs
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "external_user_123",
            "email": "external@example.com",
            "name": "External User",
        }
        mock_response.status_code = 200
        mock_client.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.post = AsyncMock(return_value=mock_response)

        mocks["http_client"] = mock_client
        yield mocks


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)

        # Mark slow tests
        if any(keyword in item.name.lower() for keyword in ["concurrent", "performance", "stress"]):
            item.add_marker(pytest.mark.slow)

        # Mark concurrent tests
        if "concurrent" in item.name.lower():
            item.add_marker(pytest.mark.concurrent)


# Fixtures for specific test scenarios
@pytest.fixture
def oauth_error_scenarios():
    """OAuth error scenarios for testing."""
    return [
        {"error": "access_denied", "error_description": "User denied access", "expected_status": 400},
        {"error": "invalid_request", "error_description": "Invalid OAuth request", "expected_status": 400},
        {"error": "unauthorized_client", "error_description": "Client not authorized", "expected_status": 400},
        {
            "error": "unsupported_response_type",
            "error_description": "Response type not supported",
            "expected_status": 400,
        },
    ]


@pytest.fixture
def rate_limit_test_scenarios():
    """Rate limiting test scenarios."""
    return {
        "oauth_normal": {"requests": 3, "window": 60, "should_pass": True},
        "oauth_exceeded": {
            "requests": 10,  # Exceeds limit of 5
            "window": 60,
            "should_pass": False,
        },
        "refresh_normal": {"requests": 5, "window": 3600, "should_pass": True},
        "refresh_exceeded": {
            "requests": 15,  # Exceeds limit of 10
            "window": 3600,
            "should_pass": False,
        },
    }


@pytest.fixture
def validation_test_cases():
    """Validation test cases for different components."""
    return {
        "oauth_callback": {
            "valid": [
                {"code": "valid_code_123", "state": "valid_state_1234567890"},
                {"code": "code-with-hyphens", "state": "state_with_underscores_123"},
                {"code": "code.with.dots", "state": "UPPERCASE_STATE_123456789"},
            ],
            "invalid": [
                {"code": "", "state": "valid_state_1234567890"},
                {"code": "code with spaces", "state": "valid_state_1234567890"},
                {"code": "code<script>", "state": "valid_state_1234567890"},
                {"code": "valid_code", "state": "short"},
                {"code": "valid_code", "state": "state with spaces 1234567890"},
            ],
        },
        "redirect_uri": {
            "valid": [
                "https://localhost/callback",
                "http://127.0.0.1:8000/auth",
                "https://testdomain.com/oauth/callback",
            ],
            "invalid": [
                "https://evil.com/callback",
                "javascript:alert('xss')",
                "ftp://localhost/callback",
                "https://localhost.evil.com/callback",
            ],
        },
    }


@pytest.fixture
def security_attack_vectors():
    """Common security attack vectors for testing."""
    return {
        "injection_attacks": {
            "sql": ["'; DROP TABLE users; --", "' OR 1=1 --"],
            "nosql": ["'; db.users.drop(); //", "' || '1'=='1"],
            "command": ["; rm -rf /", "| cat /etc/passwd"],
            "ldap": ["*)(uid=*", "admin)(&(password=*)"],
            "xpath": ["' or '1'='1", "') or ('1'='1"],
        },
        "xss_attacks": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "<iframe src=javascript:alert('xss')>",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "....//....//....//etc/passwd",
        ],
        "header_injection": [
            "value\r\nInjected-Header: malicious",
            "value\nX-Forwarded-For: evil.com",
            "value\x00null-byte-injection",
        ],
    }


# Helper functions for tests
def create_mock_request(path="/", method="GET", headers=None, params=None, client_ip="127.0.0.1"):
    """Create a mock FastAPI Request object."""
    request = Mock()
    request.url.path = path
    request.method = method
    request.headers = headers or {}
    request.query_params = params or {}
    request.client.host = client_ip
    request.url.scheme = "http"
    request.url.netloc = "localhost:8000"
    return request


def assert_validation_error(response, field_name=None, error_message=None):
    """Assert that response contains validation error."""
    assert response.status_code == 400
    data = response.json()
    assert "error" in data

    if field_name:
        assert field_name.lower() in data["message"].lower()

    if error_message:
        assert error_message in data["message"]


def assert_rate_limit_error(response):
    """Assert that response indicates rate limiting."""
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    data = response.json()
    assert data["error"] == "rate_limit_exceeded"


def assert_security_headers(response, production=False):
    """Assert that response has proper security headers."""
    headers = response.headers
    assert "X-Content-Type-Options" in headers
    assert "X-Frame-Options" in headers
    assert "X-XSS-Protection" in headers

    if production:
        assert "Strict-Transport-Security" in headers


# Export helper functions to make them available in tests
pytest.create_mock_request = create_mock_request
pytest.assert_validation_error = assert_validation_error
pytest.assert_rate_limit_error = assert_rate_limit_error
pytest.assert_security_headers = assert_security_headers
