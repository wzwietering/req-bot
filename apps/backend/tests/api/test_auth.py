import base64
import json
import logging
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
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.refresh_token_service import RefreshTokenService
from requirements_bot.core.services.user_service import UserService
from requirements_bot.core.storage import DatabaseManager


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


class TestTokenRevocation:
    """Test token revocation on new login for security."""

    @pytest.fixture
    def token_test_setup(self, test_db):
        """Setup JWT service and create test user."""
        db_manager = DatabaseManager(db_path=test_db)
        db_session_factory = db_manager.SessionLocal
        refresh_service = RefreshTokenService(db_session_factory)
        jwt_service = JWTService("a" * 32, refresh_token_service=refresh_service)

        # Create user to satisfy foreign key constraint
        with db_session_factory() as db:
            user_service = UserService(db)
            user = user_service.create_user(
                UserCreate(email="test@example.com", provider="google", provider_id="test123", name="Test User")
            )
            db.commit()
            user_id = user.id
            email = user.email

        return {
            "jwt_service": jwt_service,
            "refresh_service": refresh_service,
            "user_id": user_id,
            "email": email,
            "db_session_factory": db_session_factory,
        }

    def test_create_token_pair_revokes_existing_tokens_by_default(self, token_test_setup):
        """Test that creating a new token pair revokes all existing tokens by default."""
        jwt_service = token_test_setup["jwt_service"]
        refresh_service = token_test_setup["refresh_service"]
        user_id = token_test_setup["user_id"]
        email = token_test_setup["email"]

        # Create first token pair
        first_tokens = jwt_service.create_token_pair(user_id, email)
        first_refresh_token = first_tokens["refresh_token"]

        # Verify first token is valid
        assert refresh_service.verify_refresh_token(first_refresh_token) == user_id

        # Create second token pair (should revoke first)
        second_tokens = jwt_service.create_token_pair(user_id, email)
        second_refresh_token = second_tokens["refresh_token"]

        # Verify first token is now revoked
        assert refresh_service.verify_refresh_token(first_refresh_token) is None

        # Verify second token is valid
        assert refresh_service.verify_refresh_token(second_refresh_token) == user_id

    def test_create_token_pair_with_revoke_disabled(self, token_test_setup):
        """Test that tokens are not revoked when revoke_existing=False."""
        jwt_service = token_test_setup["jwt_service"]
        refresh_service = token_test_setup["refresh_service"]
        user_id = token_test_setup["user_id"]
        email = token_test_setup["email"]

        # Create first token pair
        first_tokens = jwt_service.create_token_pair(user_id, email, revoke_existing=False)
        first_refresh_token = first_tokens["refresh_token"]

        # Create second token pair without revoking
        second_tokens = jwt_service.create_token_pair(user_id, email, revoke_existing=False)
        second_refresh_token = second_tokens["refresh_token"]

        # Both tokens should still be valid
        assert refresh_service.verify_refresh_token(first_refresh_token) == user_id
        assert refresh_service.verify_refresh_token(second_refresh_token) == user_id

    def test_multiple_logins_only_latest_token_valid(self, token_test_setup):
        """Test that multiple logins result in only the latest token being valid."""
        jwt_service = token_test_setup["jwt_service"]
        refresh_service = token_test_setup["refresh_service"]
        user_id = token_test_setup["user_id"]
        email = token_test_setup["email"]

        # Simulate 3 logins
        token1 = jwt_service.create_token_pair(user_id, email)["refresh_token"]
        token2 = jwt_service.create_token_pair(user_id, email)["refresh_token"]
        token3 = jwt_service.create_token_pair(user_id, email)["refresh_token"]

        # Only the latest token should be valid
        assert refresh_service.verify_refresh_token(token1) is None
        assert refresh_service.verify_refresh_token(token2) is None
        assert refresh_service.verify_refresh_token(token3) == user_id

    def test_revocation_logs_count(self, token_test_setup, caplog):
        """Test that token revocation logs the number of revoked tokens."""
        caplog.set_level(logging.INFO)

        jwt_service = token_test_setup["jwt_service"]
        user_id = token_test_setup["user_id"]
        email = token_test_setup["email"]

        # Create 3 tokens without revocation
        jwt_service.create_token_pair(user_id, email, revoke_existing=False)
        jwt_service.create_token_pair(user_id, email, revoke_existing=False)
        jwt_service.create_token_pair(user_id, email, revoke_existing=False)

        # Next login should revoke all 3
        jwt_service.create_token_pair(user_id, email, revoke_existing=True)

        # Check logs for revocation event
        assert any("auth.previous_tokens_revoked" in record.message for record in caplog.records)

    def test_token_revocation_different_users(self, token_test_setup):
        """Test that revoking tokens for one user doesn't affect other users."""
        jwt_service = token_test_setup["jwt_service"]
        refresh_service = token_test_setup["refresh_service"]
        db_session_factory = token_test_setup["db_session_factory"]
        user1_id = token_test_setup["user_id"]
        email = token_test_setup["email"]

        # Create a second user
        with db_session_factory() as db:
            user_service = UserService(db)
            user2 = user_service.create_user(
                UserCreate(email="test2@example.com", provider="google", provider_id="test456", name="Test User 2")
            )
            db.commit()
            user2_id = user2.id

        # Create tokens for both users
        user1_token = jwt_service.create_token_pair(user1_id, email)["refresh_token"]
        user2_token = jwt_service.create_token_pair(user2_id, email)["refresh_token"]

        # Login again as user1 (should only revoke user1's tokens)
        jwt_service.create_token_pair(user1_id, email)

        # User1's old token should be revoked
        assert refresh_service.verify_refresh_token(user1_token) is None

        # User2's token should still be valid
        assert refresh_service.verify_refresh_token(user2_token) == user2_id
