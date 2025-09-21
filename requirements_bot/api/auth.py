import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from requirements_bot.core.models import UserCreate

logger = logging.getLogger(__name__)


class OAuth2Config(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str | None = None
    authorize_url: str | None = None
    access_token_url: str | None = None
    userinfo_endpoint: str | None = None


class JWTService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 60 * 2  # 2 hours

    def create_access_token(self, user_id: str, email: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {"sub": user_id, "email": email, "exp": expire, "iat": datetime.now(UTC)}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")

            if user_id is None or email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user information",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return {"user_id": user_id, "email": email}
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )


class OAuth2Providers:
    def __init__(self):
        self.oauth = OAuth()
        self._setup_providers()
        self._state_storage = {}  # In production, use Redis or database

    def generate_state(self) -> str:
        """Generate and store OAuth state parameter for CSRF protection."""
        state = secrets.token_urlsafe(32)
        self._state_storage[state] = datetime.now(UTC)
        return state

    def verify_state(self, state: str) -> bool:
        """Verify OAuth state parameter and remove it."""
        if state not in self._state_storage:
            return False

        # Check if state is not expired (5 minutes)
        created_at = self._state_storage.pop(state)
        if datetime.now(UTC) - created_at > timedelta(minutes=5):
            return False

        return True

    def _get_env_config(self, provider: str) -> OAuth2Config:
        client_id = os.getenv(f"{provider.upper()}_CLIENT_ID")
        client_secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError(f"Missing OAuth2 configuration for {provider}")

        return OAuth2Config(client_id=client_id, client_secret=client_secret)

    def _setup_providers(self):
        # Google OAuth2
        try:
            google_config = self._get_env_config("google")
            self.oauth.register(
                name="google",
                client_id=google_config.client_id,
                client_secret=google_config.client_secret,
                server_metadata_url="https://accounts.google.com/.well-known/openid_configuration",
                client_kwargs={"scope": "openid email profile"},
            )
        except ValueError as e:
            logger.warning(f"OAuth provider google not configured: {e}")

        # GitHub OAuth2
        try:
            github_config = self._get_env_config("github")
            self.oauth.register(
                name="github",
                client_id=github_config.client_id,
                client_secret=github_config.client_secret,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com/",
                client_kwargs={"scope": "user:email"},
            )
        except ValueError as e:
            logger.warning(f"OAuth provider github not configured: {e}")

        # Microsoft OAuth2
        try:
            microsoft_config = self._get_env_config("microsoft")
            self.oauth.register(
                name="microsoft",
                client_id=microsoft_config.client_id,
                client_secret=microsoft_config.client_secret,
                server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid_configuration",
                client_kwargs={"scope": "openid email profile"},
            )
        except ValueError as e:
            logger.warning(f"OAuth provider microsoft not configured: {e}")

    def get_provider(self, provider_name: str):
        if provider_name not in ["google", "github", "microsoft"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported OAuth provider: {provider_name}"
            )

        provider = getattr(self.oauth, provider_name, None)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth provider {provider_name} not configured",
            )

        return provider

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
def get_jwt_service() -> JWTService:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("Application configuration error")
    if len(secret_key) < 32:
        raise ValueError("Application configuration error")
    return JWTService(secret_key)


def get_oauth_providers() -> OAuth2Providers:
    return OAuth2Providers()
