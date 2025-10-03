"""User registration service for new user creation."""

import re

from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.error_responses import ValidationError
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.user_service import UserService


class UserRegistrationService:
    """Handles new user registration and creation."""

    def __init__(self, db_session: DBSession):
        self.db_session = db_session
        self.user_service = UserService(db_session)

    def register_oauth_user(self, user_create: UserCreate):
        """Register new user via OAuth provider."""
        self._validate_registration_data(user_create)
        self._check_existing_user(user_create)

        user = self.user_service.create_user(user_create)
        self.db_session.commit()
        return user

    def get_or_create_user(self, user_create: UserCreate):
        """Get existing user or create new one."""
        existing_user = self._find_existing_user(user_create)

        if existing_user:
            # Update provider info to reflect current login method
            updated_user = self._update_provider_info(existing_user, user_create)
            return updated_user
        else:
            return self.register_oauth_user(user_create)

    def _validate_registration_data(self, user_create: UserCreate):
        """Validate user registration data."""
        email = user_create.email or ""
        provider = user_create.provider or ""
        provider_id = user_create.provider_id or ""

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

    def _check_existing_user(self, user_create: UserCreate):
        """Check if user already exists."""
        email = user_create.email or ""
        if self.user_service.get_user_by_email(email):
            raise ValidationError("User already exists", "email")

    def _find_existing_user(self, user_create: UserCreate):
        """Find existing user by provider and email."""
        provider = user_create.provider or ""
        provider_id = user_create.provider_id or ""
        email = user_create.email or ""

        return self.user_service.get_user_by_provider_id(provider, provider_id) or self.user_service.get_user_by_email(
            email
        )

    def _update_provider_info(self, existing_user, user_create: UserCreate):
        """Update provider information when user logs in with different provider."""
        updated_user = self.user_service.update_user_provider(
            existing_user.id,
            user_create.provider,
            user_create.provider_id,
            user_create.name,
            user_create.avatar_url,
        )
        self.db_session.commit()
        return updated_user

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
