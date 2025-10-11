import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from requirements_bot.api.error_responses import AuthenticationError, ConfigurationError
from requirements_bot.core.logging import log_event, span
from requirements_bot.core.models import UserCreate
from requirements_bot.core.services.oauth_config_service import ConfigValidationError, OAuthConfigService
from requirements_bot.core.services.oauth_state_service import OAuthStateService
from requirements_bot.core.services.refresh_token_service import RefreshTokenService
from requirements_bot.core.services.token_config import TokenConfig

logger = logging.getLogger(__name__)


class OAuth2Config(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str | None = None
    authorize_url: str | None = None
    access_token_url: str | None = None
    userinfo_endpoint: str | None = None


class JWTService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        refresh_token_service: RefreshTokenService | None = None,
        token_config: TokenConfig | None = None,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self._token_config = token_config or TokenConfig()
        self.access_token_expire_minutes = self._token_config.access_token_expire_minutes
        self.refresh_token_service = refresh_token_service

    def create_token_pair(self, user_id: str, email: str, revoke_existing: bool = True) -> dict:
        """Create both access and refresh tokens.

        Args:
            user_id: The user's unique identifier
            email: The user's email address
            revoke_existing: If True, revokes all existing refresh tokens for this user
                           before creating new ones (recommended for security)

        Returns:
            Dictionary containing access_token, refresh_token, token_type, and expires_in
        """
        if not self.refresh_token_service:
            raise ValueError("Refresh token service not configured")

        # Security: Revoke all existing tokens before creating new ones
        # This ensures only the most recent login session is valid
        if revoke_existing:
            revoked_count = self.refresh_token_service.revoke_all_user_tokens(user_id)
            log_event(
                "auth.previous_tokens_revoked",
                level=logging.INFO,
                component="auth",
                operation="create_token_pair",
                user_id=user_id,
                tokens_revoked=revoked_count,
            )

        access_token = self.create_access_token(user_id, email)
        refresh_token = self.refresh_token_service.create_refresh_token(user_id)

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
        with span("auth.jwt_verify", component="auth", operation="verify_token"):
            try:
                log_event(
                    "auth.jwt_decode_start",
                    level=logging.DEBUG,
                    component="auth",
                    operation="verify_token",
                    token_length=len(token),
                )

                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                user_id: str | None = payload.get("sub")
                email: str | None = payload.get("email")
                exp: int | None = payload.get("exp")

                log_event(
                    "auth.jwt_decoded",
                    level=logging.DEBUG,
                    component="auth",
                    operation="verify_token",
                    has_user_id=bool(user_id),
                    has_email=bool(email),
                    has_exp=bool(exp),
                )

                if user_id is None or email is None:
                    log_event(
                        "auth.jwt_missing_claims",
                        level=logging.WARNING,
                        component="auth",
                        operation="verify_token",
                        has_user_id=bool(user_id),
                        has_email=bool(email),
                    )
                    raise AuthenticationError("Invalid token: missing user information")

                log_event(
                    "auth.jwt_verification_success",
                    level=logging.DEBUG,
                    component="auth",
                    operation="verify_token",
                    user_id=user_id,
                )

                return {"user_id": user_id, "email": email}
            except JWTError as e:
                error_type = type(e).__name__
                error_msg = str(e)

                log_event(
                    "auth.jwt_verification_failed",
                    level=logging.WARNING,
                    component="auth",
                    operation="verify_token",
                    error_type=error_type,
                    error_msg=error_msg,
                    is_expired="expired" in error_msg.lower() or "ExpiredSignature" in error_type,
                )

                # Provide more specific error messages
                if "expired" in error_msg.lower() or "ExpiredSignature" in error_type:
                    raise AuthenticationError("Token expired")
                elif "signature" in error_msg.lower():
                    raise AuthenticationError("Invalid token signature")
                else:
                    raise AuthenticationError(f"Invalid token: {error_type}")


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

    def get_provider_config(self, provider_name: str):
        """Get validated provider configuration.

        Args:
            provider_name: Name of the OAuth provider (google, github, microsoft)

        Returns:
            Validated provider configuration

        Raises:
            ConfigValidationError: If provider configuration is invalid or missing
        """
        return self._config_service.validate_provider_config(provider_name)

    def _setup_providers(self):
        """Setup OAuth providers using validated configurations."""
        for provider_name in ["google", "github", "microsoft"]:
            try:
                logger.debug(f"Attempting to configure OAuth provider: {provider_name}")
                config = self._config_service.validate_provider_config(provider_name)
                self._register_provider(provider_name, config)
                logger.info(f"OAuth provider {provider_name} configured successfully")
            except ConfigValidationError as e:
                logger.warning(f"OAuth provider {provider_name} not configured: {e}")
            except Exception as e:
                logger.error(f"Failed to setup OAuth provider {provider_name}: {type(e).__name__}")

    def _register_provider(self, provider_name: str, config):
        """Register a specific OAuth provider."""
        if provider_name == "google":
            self._register_google_provider(config)
        elif provider_name == "github":
            self._register_github_provider(config)
        elif provider_name == "microsoft":
            self._register_microsoft_provider(config)

    def _register_google_provider(self, config):
        """Register Google OAuth provider."""
        self.oauth.register(
            name="google",
            client_id=config.client_id,
            client_secret=config.client_secret,
            server_metadata_url=config.server_metadata_url,
            client_kwargs={"scope": " ".join(config.scopes)},
        )

    def _register_github_provider(self, config):
        """Register GitHub OAuth provider."""
        self.oauth.register(
            name="github",
            client_id=config.client_id,
            client_secret=config.client_secret,
            access_token_url=config.access_token_url,
            authorize_url=config.authorize_url,
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": " ".join(config.scopes)},
        )

    def _register_microsoft_provider(self, config):
        """Register Microsoft OAuth provider."""
        self.oauth.register(
            name="microsoft",
            client_id=config.client_id,
            client_secret=config.client_secret,
            server_metadata_url=config.server_metadata_url,
            client_kwargs={"scope": " ".join(config.scopes)},
        )

    def get_provider(self, provider_name: str):
        """Get OAuth provider if properly configured."""
        available_providers = self._config_service.get_available_providers()

        if provider_name not in available_providers:
            if provider_name in ["google", "github", "microsoft"]:
                logger.error(f"OAuth provider {provider_name} not properly configured")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OAuth provider {provider_name} not properly configured",
                )
            else:
                logger.error(f"Unsupported OAuth provider: {provider_name}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}"
                )

        provider = getattr(self.oauth, provider_name, None)
        if provider is None:
            logger.error(f"OAuth provider {provider_name} registration failed")
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
        # Use OpenID Connect userinfo endpoint to get proper 'sub' field
        resp = await provider.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user information from Google"
            )

        user_info = resp.json()

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
        email = await self._get_github_user_email(provider, token, user_data)

        return UserCreate(
            email=email,
            provider="github",
            provider_id=str(user_data["id"]),
            name=user_data.get("name"),
            avatar_url=user_data.get("avatar_url"),
        )

    async def _get_github_user_email(self, provider, token: dict, user_data: dict) -> str:
        """Get user email from GitHub, handling private emails."""
        email = user_data.get("email")
        if email:
            return email

        emails_resp = await provider.get("user/emails", token=token)
        if emails_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch email from GitHub")

        emails = emails_resp.json()
        primary_email = next((e for e in emails if e["primary"]), None)
        if not primary_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to retrieve email from GitHub")

        return primary_email["email"]

    async def _get_microsoft_user_info(self, token: dict) -> UserCreate:
        provider = self.oauth.microsoft
        # Use Microsoft Graph API to get user info instead of parsing ID token
        # This avoids issuer validation issues when using /common/ endpoint
        resp = await provider.get("https://graph.microsoft.com/v1.0/me", token=token)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user information from Microsoft"
            )

        user_data = resp.json()

        return UserCreate(
            email=user_data["mail"] or user_data.get("userPrincipalName"),
            provider="microsoft",
            provider_id=user_data["id"],
            name=user_data.get("displayName"),
            avatar_url=None,  # Microsoft Graph /me doesn't include photo URL by default
        )


# Global instances
def get_jwt_service(refresh_token_service: RefreshTokenService | None = None) -> JWTService:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("JWT_SECRET_KEY environment variable is not set. Please configure a secure JWT secret key.")
    if len(secret_key) < 32:
        raise ValueError(
            f"JWT_SECRET_KEY must be at least 32 characters long for security. Current length: {len(secret_key)}"
        )
    return JWTService(secret_key, refresh_token_service=refresh_token_service)


def get_oauth_providers(db_session_factory=None) -> OAuth2Providers:
    return OAuth2Providers(db_session_factory)
