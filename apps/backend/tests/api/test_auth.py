import base64
import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt

from requirements_bot.api.auth import JWTService, get_jwt_service
from requirements_bot.api.error_responses import AuthenticationError


class TestJWTTokens:
    """Test JWT token creation, validation, and management."""

    def test_jwt_service_initialization(self):
        """Test JWT service initialization with valid secret."""
        refresh_service = Mock()
        service = JWTService("a" * 32, refresh_token_service=refresh_service)

        assert service.secret_key == "a" * 32
        assert service.algorithm == "HS256"
        assert service.access_token_expire_minutes == 15

    def test_jwt_service_short_secret_error(self):
        """Test JWT service initialization with short secret key."""
        # This test verifies initialization rejects short keys (handled by get_jwt_service function)
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "short_key"}):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be at least 32 characters"):
                get_jwt_service()

    def test_create_access_token(self):
        """Test access token creation with valid payload."""
        service = JWTService("a" * 32)
        user_id = str(uuid4())
        email = "test@example.com"

        token = service.create_access_token(user_id, email)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token content
        payload = jwt.decode(token, "a" * 32, algorithms=["HS256"])
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert "exp" in payload
        assert "iat" in payload

    def test_create_token_pair(self):
        """Test creation of access and refresh token pair."""
        refresh_service = Mock()
        refresh_service.create_refresh_token.return_value = "refresh_token_123"

        service = JWTService("a" * 32, refresh_token_service=refresh_service)
        user_id = str(uuid4())
        email = "test@example.com"

        tokens = service.create_token_pair(user_id, email)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] == 900  # 15 minutes

    def test_create_token_pair_no_refresh_service(self):
        """Test token pair creation without refresh service."""
        service = JWTService("a" * 32)

        with pytest.raises(ValueError, match="Refresh token service not configured"):
            service.create_token_pair(str(uuid4()), "test@example.com")

    def test_verify_valid_token(self):
        """Test verification of valid access token."""
        service = JWTService("a" * 32)
        user_id = str(uuid4())
        email = "test@example.com"

        token = service.create_access_token(user_id, email)
        payload = service.verify_token(token)

        assert payload["user_id"] == user_id
        assert payload["email"] == email

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        service = JWTService("a" * 32)

        # Create token with past expiration
        past_time = datetime.now(UTC) - timedelta(hours=1)
        to_encode = {"sub": str(uuid4()), "email": "test@example.com", "exp": past_time, "iat": past_time}
        expired_token = jwt.encode(to_encode, "a" * 32, algorithm="HS256")

        with pytest.raises(AuthenticationError, match="Token expired"):
            service.verify_token(expired_token)

    def test_verify_malformed_token(self):
        """Test verification of malformed token."""
        service = JWTService("a" * 32)

        with pytest.raises(Exception, match="Invalid token"):
            service.verify_token("invalid.token.format")

    def test_verify_token_wrong_secret(self):
        """Test verification with wrong secret key."""
        service1 = JWTService("a" * 32)
        service2 = JWTService("b" * 32)

        token = service1.create_access_token(str(uuid4()), "test@example.com")

        with pytest.raises(Exception, match="Invalid token"):
            service2.verify_token(token)

    def test_verify_token_missing_claims(self):
        """Test verification of token with missing required claims."""
        service = JWTService("a" * 32)

        # Create token without required claims
        to_encode = {"exp": datetime.now(UTC) + timedelta(minutes=15)}
        token = jwt.encode(to_encode, "a" * 32, algorithm="HS256")

        with pytest.raises(Exception, match="Invalid token: missing user information"):
            service.verify_token(token)

    def test_refresh_access_token_success(self):
        """Test successful access token refresh."""
        refresh_service = Mock()
        refresh_service.verify_refresh_token.return_value = str(uuid4())

        service = JWTService("a" * 32, refresh_token_service=refresh_service)

        new_token = service.refresh_access_token("valid_refresh_token", "test@example.com")

        assert isinstance(new_token, str)
        refresh_service.verify_refresh_token.assert_called_once_with("valid_refresh_token")

    def test_refresh_access_token_invalid_refresh_token(self):
        """Test access token refresh with invalid refresh token."""
        refresh_service = Mock()
        refresh_service.verify_refresh_token.return_value = None

        service = JWTService("a" * 32, refresh_token_service=refresh_service)

        with pytest.raises(Exception, match="Invalid or expired refresh token"):
            service.refresh_access_token("invalid_refresh_token", "test@example.com")

    def test_refresh_access_token_no_service(self):
        """Test access token refresh without refresh token service."""
        service = JWTService("a" * 32)

        with pytest.raises(ValueError, match="Refresh token service not configured"):
            service.refresh_access_token("refresh_token", "test@example.com")


class TestAuthSecurity:
    """Test security attack vectors and protections."""

    def test_jwt_algorithm_confusion_attack(self):
        """Test protection against JWT algorithm confusion attacks."""
        service = JWTService("a" * 32)
        user_id = str(uuid4())

        # Create a properly signed token with HS256
        valid_token = service.create_access_token(user_id, "test@example.com")

        # Try to modify it to use algorithm 'none' - this should fail verification
        header, payload, signature = valid_token.split(".")

        # Create malicious header with 'none' algorithm
        malicious_header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        )

        malicious_token = f"{malicious_header}.{payload}."

        with pytest.raises(Exception, match="Invalid token"):
            service.verify_token(malicious_token)

    def test_jwt_token_tampering_detection(self):
        """Test detection of tampered JWT tokens."""
        service = JWTService("a" * 32)
        user_id = str(uuid4())

        # Create valid token
        token = service.create_access_token(user_id, "test@example.com")

        # Tamper with token by changing a character
        tampered_token = token[:-5] + "XXXXX"

        with pytest.raises(Exception, match="Invalid token"):
            service.verify_token(tampered_token)

    def test_user_profile_access_without_auth(self, client: TestClient):
        """Test access to protected profile endpoint without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_malicious_token(self, client: TestClient):
        """Test logout endpoint with malicious refresh token."""
        malicious_tokens = [
            "'; DROP TABLE refresh_tokens; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
        ]

        for malicious_token in malicious_tokens:
            response = client.post("/api/v1/auth/logout", json={"refresh_token": malicious_token})
            # Logout should succeed even with invalid token (graceful handling)
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["message"] == "Logged out successfully"

    def test_auth_status_information_disclosure(self, client: TestClient):
        """Test auth status endpoint doesn't disclose sensitive information."""
        with patch("requirements_bot.api.dependencies.get_oauth_providers_with_db") as mock_oauth:
            mock_oauth_providers = Mock()
            mock_oauth_providers.get_configuration_status.return_value = {
                "google": "configured",
                "github": "not_configured",
                "microsoft": "configured",
            }
            mock_oauth.return_value = mock_oauth_providers

            response = client.get("/api/v1/auth/status")
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert "service_status" in data
            assert "providers" in data
            assert "available_providers" in data

            # Should not contain sensitive configuration details
            assert "client_secret" not in str(data)
            assert "secret_key" not in str(data)
