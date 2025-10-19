"""User authentication service for login validation."""

from sqlalchemy.orm import Session as DBSession

from specscribe.api.error_responses import AuthenticationError
from specscribe.core.models import UserCreate
from specscribe.core.services.user_service import UserService


class UserAuthenticationService:
    """Handles user authentication and login validation."""

    def __init__(self, db_session: DBSession):
        self.db_session = db_session
        self.user_service = UserService(db_session)

    def authenticate_oauth_user(self, user_create: UserCreate):
        """Authenticate user via OAuth provider."""
        existing_user = self._find_existing_user(user_create)

        if existing_user:
            return self._validate_existing_user(existing_user, user_create)
        else:
            raise AuthenticationError("User not registered")

    def _find_existing_user(self, user_create: UserCreate):
        """Find existing user by provider and email."""
        return self.user_service.get_user_by_provider_id(
            user_create.provider, user_create.provider_id
        ) or self.user_service.get_user_by_email(user_create.email)

    def _validate_existing_user(self, user, user_create: UserCreate):
        """Validate existing user credentials."""
        if user.provider != user_create.provider:
            raise AuthenticationError(f"Account exists with different provider: {user.provider}")

        if user.provider_id != user_create.provider_id:
            raise AuthenticationError("Provider ID mismatch")

        return user
