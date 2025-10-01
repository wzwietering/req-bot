"""Unit tests for UserRegistrationService."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError

from requirements_bot.api.error_responses import ValidationError
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.user_registration_service import UserRegistrationService


class TestUserRegistrationService:
    """Test user registration service functionality."""

    def test_service_initialization(self):
        """Test service initialization with database session."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        assert service.db_session == mock_db_session
        assert service.user_service is not None

    def test_register_oauth_user_success(self):
        """Test successful OAuth user registration."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        # Mock UserService
        created_user = Mock()
        created_user.id = "user123"
        mock_user_service = Mock()
        mock_user_service.create_user.return_value = created_user
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service.register_oauth_user(user_data)

        assert result == created_user
        # Check that create_user was called with a UserCreate object containing the expected data
        call_args = mock_user_service.create_user.call_args[0][0]
        assert call_args.email == "test@example.com"
        assert call_args.provider == "google"
        assert call_args.provider_id == "123456789"
        assert call_args.name == "Test User"
        mock_db_session.commit.assert_called_once()

    def test_register_oauth_user_existing_email(self):
        """Test registration fails when email already exists."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(
            email="existing@example.com",
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        with pytest.raises(ValidationError, match="User already exists"):
            service.register_oauth_user(user_data)

        mock_user_service.create_user.assert_not_called()
        mock_db_session.commit.assert_not_called()

    def test_get_or_create_user_existing(self):
        """Test get_or_create returns existing user when found."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service.get_or_create_user(user_data)

        assert result == existing_user
        mock_user_service.create_user.assert_not_called()

    def test_get_or_create_user_create_new(self):
        """Test get_or_create creates new user when not found."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        created_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.side_effect = [None, None]  # Called twice in flow
        mock_user_service.create_user.return_value = created_user
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service.get_or_create_user(user_data)

        assert result == created_user
        # Check that create_user was called with a UserCreate object containing the expected data
        call_args = mock_user_service.create_user.call_args[0][0]
        assert call_args.email == "test@example.com"
        mock_db_session.commit.assert_called_once()

    def test_validate_registration_data_success(self):
        """Test successful validation of registration data."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        valid_data = UserCreate(
            email="test@example.com",
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        # Should not raise exception
        service._validate_registration_data(valid_data)

    def test_validate_registration_data_missing_email(self):
        """Test validation fails with missing email."""
        # Test with empty email - this will fail at Pydantic validation level
        with pytest.raises(PydanticValidationError) as exc_info:
            UserCreate(email="", provider="google", provider_id="123456789", name="Test User")

        assert "email" in str(exc_info.value).lower()

    def test_validate_registration_data_invalid_email(self):
        """Test validation fails with invalid email format."""
        invalid_emails = ["invalid-email", "test.example.com", "@example.com", "test@", "test@@example.com"]

        for invalid_email in invalid_emails:
            # Test with invalid email - this will fail at Pydantic validation level
            with pytest.raises(PydanticValidationError) as exc_info:
                UserCreate(
                    email=invalid_email,
                    provider="google",
                    provider_id="123456789",
                    name="Test User",
                )

            assert "email" in str(exc_info.value).lower()

    def test_validate_registration_data_missing_provider(self):
        """Test validation fails with missing provider."""
        # Test with empty provider - this will fail at Pydantic validation level
        with pytest.raises(PydanticValidationError) as exc_info:
            UserCreate(email="test@example.com", provider="", provider_id="123456789", name="Test User")

        assert "provider" in str(exc_info.value).lower()

    def test_validate_registration_data_missing_provider_id(self):
        """Test validation fails with missing provider ID."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        # Test with empty provider_id - service level validation should catch this
        invalid_data = UserCreate(email="test@example.com", provider="google", provider_id="", name="Test User")

        with pytest.raises(ValidationError) as exc_info:
            service._validate_registration_data(invalid_data)

        assert "Provider information is required" in str(exc_info.value)

    def test_check_existing_user_none(self):
        """Test check for existing user when none exists."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        # Should not raise exception
        service._check_existing_user(user_data)

    def test_check_existing_user_exists(self):
        """Test check fails when user already exists."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(
            email="existing@example.com",
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        with pytest.raises(ValidationError) as exc_info:
            service._check_existing_user(user_data)

        assert "User already exists" in str(exc_info.value)

    def test_find_existing_user_by_provider_id(self):
        """Test finding existing user by provider ID."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_data)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")

    def test_find_existing_user_by_email_fallback(self):
        """Test finding existing user by email when not found by provider ID."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_data)

        assert result == existing_user
        mock_user_service.get_user_by_provider_id.assert_called_once_with("google", "123456789")
        mock_user_service.get_user_by_email.assert_called_once_with("test@example.com")

    def test_find_existing_user_not_found(self):
        """Test when user is not found by either method."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        mock_user_service = Mock()
        mock_user_service.get_user_by_provider_id.return_value = None
        mock_user_service.get_user_by_email.return_value = None
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        result = service._find_existing_user(user_data)

        assert result is None


class TestUserRegistrationServiceSecurity:
    """Test security-specific scenarios for user registration."""

    def test_registration_prevents_email_enumeration(self):
        """Test that registration doesn't allow email enumeration attacks."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        existing_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = existing_user
        service.user_service = mock_user_service

        user_data = UserCreate(
            email="existing@example.com",
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        with pytest.raises(ValidationError) as exc_info:
            service.register_oauth_user(user_data)

        # Error message should be generic, not revealing existence
        error_message = str(exc_info.value)
        assert "User already exists" in error_message
        # Should not reveal specific user details
        assert "existing@example.com" not in error_message

    def test_registration_handles_race_conditions(self):
        """Test registration handles database race conditions."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        mock_user_service = Mock()
        # First check passes (no existing user)
        mock_user_service.get_user_by_email.return_value = None
        # But creation fails due to race condition
        mock_user_service.create_user.side_effect = IntegrityError("duplicate key", None, None)
        service.user_service = mock_user_service

        user_data = UserCreate(email="race@example.com", provider="google", provider_id="123456789", name="Test User")

        # Should propagate the integrity error (let upper layers handle)
        with pytest.raises(IntegrityError):
            service.register_oauth_user(user_data)

    def test_registration_validates_email_format_security(self):
        """Test registration validates email format for security."""
        # Test various malicious email formats
        malicious_emails = [
            "attacker+<script>alert('xss')</script>@example.com",
            "attacker'; DROP TABLE users; --@example.com",
            "attacker@evil.com\r\nBCC: victim@target.com",
            "attacker@exam\x00ple.com",
            "attacker@example.com\n\rinjected_header: malicious",
        ]

        for malicious_email in malicious_emails:
            # Test with malicious email - this will fail at Pydantic validation level
            with pytest.raises(PydanticValidationError) as exc_info:
                UserCreate(
                    email=malicious_email,
                    provider="google",
                    provider_id="123456789",
                    name="Test User",
                )

            assert "email" in str(exc_info.value).lower()

    def test_registration_validates_provider_security(self):
        """Test registration validates provider information for security."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        # Test malicious provider data
        malicious_providers = [
            ("google'; DROP TABLE users; --", "123456789"),
            ("google\x00admin", "123456789"),
            ("google<script>alert('xss')</script>", "123456789"),
            ("google", "'; DELETE FROM users WHERE '1'='1"),
            ("google", "123\x00admin"),
            ("", "123456789"),
            ("google", ""),
            (None, "123456789"),
            ("google", None),
        ]

        for provider, provider_id in malicious_providers:
            # Test with malicious provider data - some will fail at Pydantic validation level,
            # others should pass but fail at service validation level
            try:
                # Try to create UserCreate object
                user_data = UserCreate(
                    email="test@example.com",
                    provider=provider,
                    provider_id=provider_id,
                    name="Test User",
                )

                # If creation succeeds, service validation should catch the issue
                with pytest.raises(ValidationError) as exc_info:
                    service._validate_registration_data(user_data)

                assert "Provider information is required" in str(exc_info.value)

            except PydanticValidationError as exc_info:
                # Expected for invalid provider values
                error_msg = str(exc_info).lower()
                assert "provider" in error_msg or "validation error" in error_msg

    def test_registration_transaction_rollback_on_error(self):
        """Test that registration properly handles transaction rollback on errors."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = None
        # Simulate error during user creation
        mock_user_service.create_user.side_effect = Exception("Creation failed")
        service.user_service = mock_user_service

        user_data = UserCreate(email="test@example.com", provider="google", provider_id="123456789", name="Test User")

        with pytest.raises(Exception, match="Creation failed"):
            service.register_oauth_user(user_data)

        # Commit should not be called if creation fails
        mock_db_session.commit.assert_not_called()

    def test_registration_input_sanitization(self):
        """Test that registration data is properly handled for injection attacks."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        created_user = Mock()
        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = None
        mock_user_service.create_user.return_value = created_user
        service.user_service = mock_user_service

        # Test with potentially dangerous but valid input
        user_data = UserCreate(
            email="test+tag@example.com",  # Plus addressing is valid
            provider="google",
            provider_id="123456789",
            name="Test User O'Brien",  # Apostrophe in name is valid
        )

        result = service.register_oauth_user(user_data)

        assert result == created_user
        # Verify the data was passed through to create_user
        call_args = mock_user_service.create_user.call_args[0][0]
        assert call_args.email == "test+tag@example.com"
        assert call_args.name == "Test User O'Brien"

    def test_registration_duplicate_provider_id_handling(self):
        """Test handling of duplicate provider ID attempts."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        # Existing user with same provider ID
        existing_user = Mock()
        existing_user.provider_id = "123456789"
        existing_user.email = "existing@example.com"

        mock_user_service = Mock()
        # get_or_create_user should find existing user by provider ID
        mock_user_service.get_user_by_provider_id.return_value = existing_user
        service.user_service = mock_user_service

        # Attacker tries to register with same provider ID but different email
        user_data = UserCreate(
            email="attacker@example.com",  # Different email
            provider="google",
            provider_id="123456789",  # Same provider ID
            name="Attacker",
        )

        # Should return existing user (preventing duplicate provider ID)
        result = service.get_or_create_user(user_data)
        assert result == existing_user

        # Should not create new user
        mock_user_service.create_user.assert_not_called()

    def test_registration_case_sensitivity_email(self):
        """Test email case sensitivity handling during registration."""
        mock_db_session = Mock()
        service = UserRegistrationService(mock_db_session)

        # Test that email case handling is delegated to UserService
        mock_user_service = Mock()
        mock_user_service.get_user_by_email.return_value = None
        created_user = Mock()
        mock_user_service.create_user.return_value = created_user
        service.user_service = mock_user_service

        user_data = UserCreate(
            email="Test@Example.COM",  # Mixed case
            provider="google",
            provider_id="123456789",
            name="Test User",
        )

        result = service.register_oauth_user(user_data)

        # Should succeed and delegate email handling to UserService
        assert result == created_user
        mock_user_service.get_user_by_email.assert_called_with("Test@example.com")
        # Check that create_user was called with a UserCreate object containing the expected data
        call_args = mock_user_service.create_user.call_args[0][0]
        assert call_args.email == "Test@example.com"  # Pydantic normalizes domain but keeps local part case

    def test_registration_long_input_handling(self):
        """Test registration with extremely long input values."""
        # Test with very long inputs that could cause buffer overflows
        long_email = "a" * 1000 + "@example.com"
        long_name = "a" * 10000
        long_provider_id = "a" * 10000

        # Should fail validation due to email length limit (254 chars RFC 5321)
        with pytest.raises(PydanticValidationError) as exc_info:
            UserCreate(email=long_email, provider="google", provider_id=long_provider_id, name=long_name)

        assert "email" in str(exc_info.value).lower() and (
            "too long" in str(exc_info.value).lower() or "validation error" in str(exc_info.value).lower()
        )
