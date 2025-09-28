import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.auth import JWTService, OAuth2Providers
from requirements_bot.api.dependencies import (
    get_database_session,
    get_jwt_service_with_refresh,
    get_oauth_providers_with_db,
    get_refresh_token_service,
)
from requirements_bot.api.error_responses import (
    AuthenticationError,
    NotFoundError,
    OAuthError,
    ValidationError,
    create_error_response,
)
from requirements_bot.api.rate_limiting import rate_limit_middleware
from requirements_bot.core.models import UserResponse
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator
from requirements_bot.core.services.oauth_redirect_config import OAuthRedirectConfig
from requirements_bot.core.services.refresh_token_service import RefreshTokenService
from requirements_bot.core.services.user_registration_service import UserRegistrationService
from requirements_bot.core.services.user_service import UserService

logger = logging.getLogger(__name__)


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        if not v or not v.strip():
            raise ValueError("Refresh token cannot be empty")
        if len(v) < 10:
            raise ValueError("Refresh token appears to be invalid")
        return v.strip()


class LogoutRequest(BaseModel):
    refresh_token: str | None = None

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Refresh token cannot be empty if provided")
            if len(v) < 10:
                raise ValueError("Refresh token appears to be invalid")
            return v.strip()
        return v


router = APIRouter(prefix="/auth", tags=["authentication"])


def validate_provider_name(provider: str) -> str:
    """Validate OAuth provider name."""
    if not provider or not provider.strip():
        raise ValidationError("Provider name cannot be empty", "provider")

    provider = provider.strip().lower()
    if provider not in ["google", "github", "microsoft"]:
        raise ValidationError(f"Unsupported provider: {provider}", "provider")

    return provider


def _validate_oauth_callback(request: Request, oauth_providers: OAuth2Providers, provider: str) -> dict:
    """Validate OAuth callback parameters and state."""
    validator = OAuthCallbackValidator()
    params = validator.validate_callback_params(request, provider)

    if not oauth_providers.verify_state(params["state"]):
        raise OAuthError("Invalid or expired state parameter", provider)

    return params


async def _exchange_oauth_token(oauth_client, request: Request, provider: str):
    """Exchange authorization code for OAuth token."""
    token = await oauth_client.authorize_access_token(request)
    if not token:
        raise OAuthError("Failed to obtain access token", provider)
    return token


async def _process_oauth_user(
    oauth_providers: OAuth2Providers, provider: str, token: dict, db_session: DBSession, jwt_service: JWTService
):
    """Process OAuth user information and create session."""
    user_create = await oauth_providers.get_user_info(provider, token)
    return _create_user_session(user_create, db_session, jwt_service)


def _create_user_session(user_create, db_session: DBSession, jwt_service: JWTService):
    """Create user and generate session tokens."""
    registration_service = UserRegistrationService(db_session)
    user = registration_service.get_or_create_user(user_create)

    user_service = UserService(db_session)
    token_data = jwt_service.create_token_pair(user.id, user.email)
    response = token_data.copy()
    response["user"] = user_service.to_response(user)
    return response


@router.get("/login/{provider}")
async def oauth_login(
    provider: str,
    request: Request,
    oauth_providers: Annotated[OAuth2Providers, Depends(get_oauth_providers_with_db)],
):
    """Initiate OAuth login with specified provider."""
    rate_limit_middleware.check_oauth_rate_limit(request)
    provider = validate_provider_name(provider)

    try:
        oauth_client = oauth_providers.get_provider(provider)
        state = oauth_providers.generate_state()

        redirect_config = OAuthRedirectConfig()
        callback_url = redirect_config.build_callback_url(request, provider)

        redirect_url = await oauth_client.authorize_redirect(request, callback_url, state=state)
        return redirect_url

    except HTTPException:
        raise
    except Exception as e:
        raise create_error_response(
            "oauth_login_failed", "Failed to initiate OAuth login", status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
    oauth_providers: Annotated[OAuth2Providers, Depends(get_oauth_providers_with_db)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service_with_refresh)],
):
    """Handle OAuth callback and create user session."""
    rate_limit_middleware.check_oauth_rate_limit(request)
    provider = validate_provider_name(provider)

    try:
        oauth_client = oauth_providers.get_provider(provider)
        _validate_oauth_callback(request, oauth_providers, provider)
        token = await _exchange_oauth_token(oauth_client, request, provider)
        result = await _process_oauth_user(oauth_providers, provider, token, db_session, jwt_service)
        return result
    except HTTPException:
        db_session.rollback()
        raise
    except Exception as e:
        db_session.rollback()
        raise create_error_response(
            "oauth_callback_failed", "OAuth authentication process failed", status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
):
    """Get current authenticated user profile."""
    # User info is set by AuthenticationMiddleware
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthenticationError()

    user_service = UserService(db_session)
    user = user_service.get_user_by_id(user_id)

    if not user:
        raise NotFoundError("User", user_id)

    return user_service.to_response(user)


@router.post("/refresh")
async def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service_with_refresh)],
):
    """Refresh access token using refresh token."""
    rate_limit_middleware.check_refresh_token_rate_limit(request)

    try:
        refresh_token_service = RefreshTokenService(lambda: db_session)
        user_id = refresh_token_service.verify_refresh_token(request_data.refresh_token)

        if not user_id:
            raise AuthenticationError("Invalid or expired refresh token")

        # Get user info for new access token
        user_service = UserService(db_session)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise NotFoundError("User", user_id)

        # Create new access token
        access_token = jwt_service.create_access_token(user.id, user.email)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": jwt_service.access_token_expire_minutes * 60,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise create_error_response(
            "token_refresh_failed", "Failed to refresh access token", status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e


@router.post("/logout")
async def logout(
    request_data: LogoutRequest,
    refresh_token_service: Annotated[RefreshTokenService, Depends(get_refresh_token_service)],
):
    """Logout user and revoke refresh token."""
    try:
        if request_data.refresh_token:
            refresh_token_service.revoke_refresh_token(request_data.refresh_token)

        return {"message": "Logged out successfully"}

    except Exception:
        # Don't fail logout even if token revocation fails
        return {"message": "Logged out successfully"}


@router.get("/status")
async def auth_status(
    oauth_providers: Annotated[OAuth2Providers, Depends(get_oauth_providers_with_db)],
):
    """Get authentication system status and provider configurations."""
    try:
        provider_status = oauth_providers.get_configuration_status()
        available_providers = [p for p, status in provider_status.items() if status == "configured"]

        return {
            "service_status": "operational",
            "providers": provider_status,
            "available_providers": available_providers,
        }

    except Exception as e:
        raise create_error_response(
            "status_check_failed",
            "Failed to check authentication service status",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e
