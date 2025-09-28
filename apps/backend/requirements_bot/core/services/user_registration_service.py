"""User registration service for new user creation."""

import re
from typing import Any

from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.error_responses import ValidationError
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.user_service import UserService


class UserRegistrationService:
    """Handles new user registration and creation."""

    def __init__(self, db_session: DBSession):
        self.db_session = db_session
        self.user_service = UserService(db_session)

    def register_oauth_user(self, user_data: dict[str, Any]):
        """Register new user via OAuth provider."""
        self._validate_registration_data(user_data)
        self._check_existing_user(user_data)

        user_create = UserCreate(**user_data)
        user = self.user_service.create_user(user_create)
        self.db_session.commit()
        return user

    def get_or_create_user(self, user_data: dict[str, Any]):
        """Get existing user or create new one."""
        existing_user = self._find_existing_user(user_data)

        if existing_user:
            return existing_user
        else:
            return self.register_oauth_user(user_data)

    def _validate_registration_data(self, user_data: dict[str, Any]):
        """Validate user registration data."""
        email = user_data.get("email", "")
        provider = user_data.get("provider", "")
        provider_id = user_data.get("provider_id", "")

        # Validate email
        if not email:
            raise ValidationError("Valid email is required", "email")

        if not self._is_valid_email(email):
            raise ValidationError("Valid email is required", "email")

        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address too long", "email")

        # Validate provider information
        if not provider or provider is None or not provider_id or provider_id is None:
            raise ValidationError("Provider information is required", "provider")

        # Also check for invalid characters and malicious content
        if isinstance(provider, str) and (
            any(char in provider for char in ["\n", "\r", "\x00", "<", ">", ";", "'", '"'])
            or provider not in ["google", "github", "microsoft"]
        ):
            raise ValidationError("Provider information is required", "provider")

        if isinstance(provider_id, str) and any(
            char in provider_id for char in ["\n", "\r", "\x00", "<", ">", ";", "'"]
        ):
            raise ValidationError("Provider information is required", "provider")

    def _check_existing_user(self, user_data: dict[str, Any]):
        """Check if user already exists."""
        email = user_data.get("email", "")
        if self.user_service.get_user_by_email(email):
            raise ValidationError("User already exists", "email")

    def _find_existing_user(self, user_data: dict[str, Any]):
        """Find existing user by provider and email."""
        provider = user_data.get("provider", "")
        provider_id = user_data.get("provider_id", "")
        email = user_data.get("email", "")

        return self.user_service.get_user_by_provider_id(provider, provider_id) or self.user_service.get_user_by_email(
            email
        )

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format with security checks."""
        if not email:
            return False

        # Basic format check
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False

        # Security checks for malicious content
        if any(char in email for char in ["\n", "\r", "\x00", "<", ">"]):
            return False

        # Check for script tags or SQL injection attempts
        lower_email = email.lower()
        if any(dangerous in lower_email for dangerous in ["<script", "drop table", "delete from"]):
            return False

        return True
