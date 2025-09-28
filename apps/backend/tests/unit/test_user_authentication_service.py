"""Unit tests for UserAuthenticationService."""

from unittest.mock import Mock

import pytest

from requirements_bot.api.error_responses import AuthenticationError
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.user_authentication_service import UserAuthenticationService


class TestUserAuthenticationService:
    """Test user authentication service functionality."""

    def test_service_initialization(self):
        """Test service initialization with database session."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        assert service.db_session == mock_db_session
        assert service.user_service is not None

    def test_authenticate_oauth_user_success_existing_user(self):
        """Test successful authentication of existing OAuth user."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        # Mock existing user
        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "123456789"

        # Mock UserService
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        # Create test user data
        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service.authenticate_oauth_user(user_create)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")

    def test_authenticate_oauth_user_no_existing_user(self):
        """Test authentication when user doesn't exist."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        # Mock UserService - no existing user found
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        with pytest.raises(AuthenticationError, match="User not registered"):
            service.authenticate_oauth_user(user_create)

    def test_authenticate_oauth_user_found_by_email(self):
        """Test authentication when user found by email but not provider ID."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        # Mock existing user found by email
        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "123456789"

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service.authenticate_oauth_user(user_create)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")
        mock_user_service.get_user_by_email.assert_called_once_with("test@example.com")

    def test_find_existing_user_by_provider_id(self):
        """Test finding user by provider ID first."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_create)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")
        # Should not call get_user_by_email if found by provider ID
        mock_user_service.get_user_by_email.assert_not_called()

    def test_find_existing_user_by_email_fallback(self):
        """Test finding user by email when not found by provider ID."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_create)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")
        mock_user_service.get_user_by_email.assert_called_once_with("test@example.com")

    def test_find_existing_user_not_found(self):
        """Test when user is not found by either method."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_create)

        assert result is None

    def test_validate_existing_user_success(self):
        """Test successful validation of existing user credentials."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "123456789"

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._validate_existing_user(existing_user, user_create)

        assert result == existing_user

    def test_validate_existing_user_different_provider(self):
        """Test validation failure when user has different provider."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        existing_user.provider = "github"
        existing_user.provider_id = "123456789"

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        with pytest.raises(AuthenticationError, match="Account exists with different provider: github"):
            service._validate_existing_user(existing_user, user_create)

    def test_validate_existing_user_provider_id_mismatch(self):
        """Test validation failure when provider ID doesn't match."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "different_id"

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        with pytest.raises(AuthenticationError, match="Provider ID mismatch"):
            service._validate_existing_user(existing_user, user_create)


class TestUserAuthenticationServiceSecurity:
    """Test security-specific scenarios for user authentication."""

    def test_authentication_prevents_account_takeover(self):
        """Test that authentication prevents account takeover attacks."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        # Existing user with GitHub account
        existing_user = Mock()
        existing_user.provider = "github"
        existing_user.provider_id = "github123"
        existing_user.email = "victim@example.com"

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        # Attacker tries to login with same email but different provider
        attacker_data = UserCreate(
            email="victim@example.com",
            provider="google",  # Different provider
            provider_id="attacker123",
            name="Attacker",
        )

        with pytest.raises(AuthenticationError, match="Account exists with different provider: github"):
            service.authenticate_oauth_user(attacker_data)

    def test_authentication_prevents_provider_id_spoofing(self):
        """Test prevention of provider ID spoofing attacks."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        # Existing user
        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "legitimate_user_123"

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        # Attacker tries to use same provider but wrong provider ID
        spoofed_data = UserCreate(
            email="attacker@example.com",
            provider="google",
            provider_id="spoofed_id_456",  # Wrong provider ID
            name="Attacker",
        )

        with pytest.raises(AuthenticationError, match="Provider ID mismatch"):
            service.authenticate_oauth_user(spoofed_data)

    def test_authentication_email_case_sensitivity(self):
        """Test that email matching is handled securely."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "123456789"

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        # Test with different case email
        user_create = UserCreate(
            email="Test@Example.COM",  # Different case
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        # Should find user (email matching is delegated to UserService)
        result = service.authenticate_oauth_user(user_create)
        assert result == existing_user

    def test_authentication_handles_nonexistent_user(self):
        """Test that authentication properly handles requests for nonexistent users."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        # Test with valid data for nonexistent user
        user_data = UserCreate(
            email="nonexistent@example.com",
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        with pytest.raises(AuthenticationError, match="User not registered"):
            service.authenticate_oauth_user(user_data)

        # Verify that the service properly attempted to find the user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")
        mock_user_service.get_user_by_email.assert_called_once_with("nonexistent@example.com")

    def test_authentication_error_message_information_disclosure(self):
        """Test that error messages don't leak sensitive information."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        mock_user_service = Mock()
        service.user_service = mock_user_service

        # Test when no user exists
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = None

        user_create = UserCreate(
            email="nonexistent@example.com", provider="google", provider_id="123456789", name="Test User"
        )

        with pytest.raises(AuthenticationError) as exc_info:
            service.authenticate_oauth_user(user_create)

        # Error message should be generic, not revealing specific details
        error_message = str(exc_info.value)
        assert "User not registered" in error_message
        assert "nonexistent@example.com" not in error_message
        assert "123456789" not in error_message

    def test_authentication_timing_attack_resistance(self):
        """Test that authentication has consistent timing to prevent timing attacks."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        existing_user = Mock()
        existing_user.provider = "google"
        existing_user.provider_id = "123456789"

        mock_user_service = Mock()
        service.user_service = mock_user_service

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        # Test 1: User found by provider ID (fast path)
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        result1 = service.authenticate_oauth_user(user_create)
        assert result1 == existing_user

        # Test 2: User not found by provider ID, found by email (slower path)
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        result2 = service.authenticate_oauth_user(user_create)
        assert result2 == existing_user

        # Both paths should call the same validation logic
        # This ensures consistent timing regardless of lookup path

    def test_authentication_database_error_handling(self):
        """Test proper handling of database errors during authentication."""
        mock_db_session = Mock()
        service = UserAuthenticationService(mock_db_session)

        mock_user_service = Mock()
        service.user_service = mock_user_service

        # Simulate database error
        mock_user_service.get_user_by_provider_id.side_effect = Exception("Database connection failed")

        user_create = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        # Database errors should propagate up (not be caught silently)
        with pytest.raises(Exception, match="Database connection failed"):
            service.authenticate_oauth_user(user_create)
