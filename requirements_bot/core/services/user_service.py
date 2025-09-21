from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from requirements_bot.core.database_models import UserTable
from requirements_bot.core.models import User, UserCreate, UserResponse


class UserService:
    def __init__(self, db_session: DBSession):
        self.db_session = db_session

    def create_user(self, user_create: UserCreate) -> User:
        """Create a new user or return existing user with same provider."""
        existing_user = self.get_user_by_provider(user_create.provider, user_create.provider_id)
        if existing_user:
            return existing_user

        user_table = UserTable(
            email=user_create.email,
            provider=user_create.provider,
            provider_id=user_create.provider_id,
            name=user_create.name,
            avatar_url=user_create.avatar_url,
        )

        self.db_session.add(user_table)
        self.db_session.flush()
        self.db_session.refresh(user_table)

        return self._table_to_model(user_table)

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        query = select(UserTable).where(UserTable.id == user_id)
        user_table = self.db_session.execute(query).scalar_one_or_none()

        if user_table:
            return self._table_to_model(user_table)
        return None

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        query = select(UserTable).where(UserTable.email == email)
        user_table = self.db_session.execute(query).scalar_one_or_none()

        if user_table:
            return self._table_to_model(user_table)
        return None

    def get_user_by_provider(self, provider: str, provider_id: str) -> User | None:
        """Get user by OAuth provider and provider ID."""
        query = select(UserTable).where(UserTable.provider == provider, UserTable.provider_id == provider_id)
        user_table = self.db_session.execute(query).scalar_one_or_none()

        if user_table:
            return self._table_to_model(user_table)
        return None

    def update_user(self, user_id: str, user_update: UserCreate) -> User | None:
        """Update user information."""
        query = select(UserTable).where(UserTable.id == user_id)
        user_table = self.db_session.execute(query).scalar_one_or_none()

        if not user_table:
            return None

        user_table.email = user_update.email
        user_table.name = user_update.name
        user_table.avatar_url = user_update.avatar_url

        self.db_session.flush()
        self.db_session.refresh(user_table)

        return self._table_to_model(user_table)

    def _table_to_model(self, user_table: UserTable) -> User:
        """Convert UserTable to User model."""
        return User(
            id=user_table.id,
            email=user_table.email,
            provider=user_table.provider,
            provider_id=user_table.provider_id,
            name=user_table.name,
            avatar_url=user_table.avatar_url,
            created_at=user_table.created_at,
            updated_at=user_table.updated_at,
        )

    def to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse."""
        return UserResponse(
            id=user.id,
            email=user.email,
            provider=user.provider,
            name=user.name,
            avatar_url=user.avatar_url,
            created_at=user.created_at,
        )
