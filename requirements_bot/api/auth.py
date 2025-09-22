import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from requirements_bot.api.error_responses import AuthenticationError, ConfigurationError
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.oauth_config_service import ConfigValidationError, OAuthConfigService
from requirements_bot.core.services.oauth_state_service import OAuthStateService
from requirements_bot.core.services.refresh_token_service import RefreshTokenService

logger = logging.getLogger(__name__)


class OAuth2Config(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str | None = None
    authorize_url: str | None = None
    access_token_url: str | None = None
    userinfo_endpoint: str | None = None


class JWTService:
    def __init__(self, secret_key: str, algorithm: str = "HS256", refresh_token_service: RefreshTokenService = None):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 15  # Shorter for access tokens
        self.refresh_token_service = refresh_token_service

    def create_token_pair(self, user_id: str, email: str) -> dict:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user_id, email)

        if self.refresh_token_service:
            refresh_token = self.refresh_token_service.create_refresh_token(user_id)
        else:
            raise ValueError("Refresh token service not configured")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
        }

    def create_access_token(self, user_id: str, email: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {"sub": user_id, "email": email, "exp": expire, "iat": datetime.now(UTC)}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def refresh_access_token(self, refresh_token: str, user_email: str) -> str:
        """Create new access token using refresh token."""
        if not self.refresh_token_service:
            raise ValueError("Refresh token service not configured")

        user_id = self.refresh_token_service.verify_refresh_token(refresh_token)
        if not user_id:
            raise AuthenticationError("Invalid or expired refresh token")

        return self.create_access_token(user_id, user_email)

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")

            if user_id is None or email is None:
                raise AuthenticationError("Invalid token: missing user information")

            return {"user_id": user_id, "email": email}
        except JWTError:
            raise AuthenticationError("Invalid token")


class OAuth2Providers:
    def __init__(self, db_session_factory=None):
        self.oauth = OAuth()
        self._state_service = OAuthStateService(db_session_factory) if db_session_factory else None
        self._config_service = OAuthConfigService()
        self._setup_providers()

    def generate_state(self) -> str:
        """Generate and store OAuth state parameter for CSRF protection."""
        if not self._state_service:
            raise ConfigurationError("Database session factory not configured")
        return self._state_service.generate_state()

    def verify_state(self, state: str) -> bool:
        """Verify OAuth state parameter and remove it."""
        if not self._state_service:
            raise ConfigurationError("Database session factory not configured")
        return self._state_service.verify_and_consume_state(state)

    def _setup_providers(self):
        """Setup OAuth providers using validated configurations."""
        for provider_name in ["google", "github", "microsoft"]:
            try:
                config = self._config_service.validate_provider_config(provider_name)

                if provider_name == "google":
                    self.oauth.register(
                        name="google",
                        client_id=config.client_id,
                        client_secret=config.client_secret,
                        server_metadata_url=config.server_metadata_url,
                        client_kwargs={"scope": " ".join(config.scopes)},
                    )
                elif provider_name == "github":
                    self.oauth.register(
                        name="github",
                        client_id=config.client_id,
                        client_secret=config.client_secret,
                        access_token_url=config.access_token_url,
                        authorize_url=config.authorize_url,
                        api_base_url="https://api.github.com/",
                        client_kwargs={"scope": " ".join(config.scopes)},
                    )
                elif provider_name == "microsoft":
                    self.oauth.register(
                        name="microsoft",
                        client_id=config.client_id,
                        client_secret=config.client_secret,
                        server_metadata_url=config.server_metadata_url,
                        client_kwargs={"scope": " ".join(config.scopes)},
                    )

                logger.info(f"OAuth provider {provider_name} configured successfully")

            except ConfigValidationError as e:
                logger.warning(f"OAuth provider {provider_name} not configured: {e}")

    def get_provider(self, provider_name: str):
        """Get OAuth provider if properly configured."""
        available_providers = self._config_service.get_available_providers()

        if provider_name not in available_providers:
            if provider_name in ["google", "github", "microsoft"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OAuth provider {provider_name} not properly configured",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}"
                )

        provider = getattr(self.oauth, provider_name, None)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth provider {provider_name} registration failed",
            )

        return provider

    def get_configuration_status(self) -> dict:
        """Get configuration status for all providers."""
        return self._config_service.validate_all_configurations()

    async def get_user_info(self, provider_name: str, token: dict) -> UserCreate:
        if provider_name == "google":
            return await self._get_google_user_info(token)
        elif provider_name == "github":
            return await self._get_github_user_info(token)
        elif provider_name == "microsoft":
            return await self._get_microsoft_user_info(token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider: {provider_name}"
            )

    async def _get_google_user_info(self, token: dict) -> UserCreate:
        provider = self.oauth.google
        user_info = await provider.parse_id_token(token)

        return UserCreate(
            email=user_info["email"],
            provider="google",
            provider_id=user_info["sub"],
            name=user_info.get("name"),
            avatar_url=user_info.get("picture"),
        )

    async def _get_github_user_info(self, token: dict) -> UserCreate:
        provider = self.oauth.github
        resp = await provider.get("user", token=token)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user information from GitHub"
            )

        user_data = resp.json()

        # Get primary email if not public
        email = user_data.get("email")
        if not email:
            emails_resp = await provider.get("user/emails", token=token)
            if emails_resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch email from GitHub")
            emails = emails_resp.json()
            primary_email = next((e for e in emails if e["primary"]), None)
            email = primary_email["email"] if primary_email else None

        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to retrieve email from GitHub")

        return UserCreate(
            email=email,
            provider="github",
            provider_id=str(user_data["id"]),
            name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
        )

    async def _get_microsoft_user_info(self, token: dict) -> UserCreate:
        provider = self.oauth.microsoft
        user_info = await provider.parse_id_token(token)

        return UserCreate(
            email=user_info["email"],
            provider="microsoft",
            provider_id=user_info["sub"],
            name=user_info.get("name"),
            avatar_url=None,  # Microsoft doesn't provide avatar in ID token
        )


# Global instances
def get_jwt_service(refresh_token_service: RefreshTokenService = None) -> JWTService:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("Application configuration error")
    if len(secret_key) < 32:
        raise ValueError("Application configuration error")
    return JWTService(secret_key, refresh_token_service=refresh_token_service)


def get_oauth_providers(db_session_factory=None) -> OAuth2Providers:
    return OAuth2Providers(db_session_factory)
