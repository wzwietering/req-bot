import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session as DBSession

from requirements_bot.api.auth import JWTService, OAuth2Providers
from requirements_bot.api.dependencies import (
    get_database_session,
    get_jwt_service_with_refresh,
    get_oauth_providers_with_db,
    get_refresh_token_service,
    get_session_cookie_config,
)
from requirements_bot.api.error_responses import (
    AuthenticationError,
    NotFoundError,
    OAuthError,
    ValidationError,
    create_error_response,
)
from requirements_bot.api.rate_limiting import rate_limit_middleware
from requirements_bot.core.logging import log_event, mask_text, span
from requirements_bot.core.models import UserResponse
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator
from requirements_bot.core.services.oauth_redirect_config import OAuthRedirectConfig
from requirements_bot.core.services.refresh_token_service import RefreshTokenService
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig
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
    with span(
        "oauth.validate_callback",
        component="auth",
        operation="validate_callback",
        provider=provider,
    ):
        validator = OAuthCallbackValidator()
        params = validator.validate_callback_params(request, provider)

        log_event(
            "oauth.callback_params_validated",
            component="auth",
            operation="validate_callback",
            provider=provider,
            has_code=bool(params.get("code")),
            has_state=bool(params.get("state")),
            code_length=len(params.get("code", "")),
            state_length=len(params.get("state", "")),
        )

        # Verify state parameter
        state_valid = oauth_providers.verify_state(params["state"])
        log_event(
            "oauth.state_verification",
            component="auth",
            operation="verify_state",
            provider=provider,
            state_valid=state_valid,
            state_prefix=mask_text(params["state"])[:8] if params.get("state") else None,
        )

        if not state_valid:
            raise OAuthError("Invalid or expired state parameter", provider)

        return params


async def _exchange_oauth_token(oauth_client, request: Request, provider: str):
    """Exchange authorization code for OAuth token."""
    with span(
        "oauth.exchange_token",
        component="auth",
        operation="exchange_token",
        provider=provider,
    ):
        log_event(
            "oauth.token_exchange_start",
            component="auth",
            operation="exchange_token",
            provider=provider,
        )

        token = await oauth_client.authorize_access_token(request)

        has_access_token = bool(token and token.get("access_token"))
        has_token_type = bool(token and token.get("token_type"))

        log_event(
            "oauth.token_exchange_result",
            component="auth",
            operation="exchange_token",
            provider=provider,
            success=bool(token),
            has_access_token=has_access_token,
            has_token_type=has_token_type,
            token_type=token.get("token_type") if token else None,
        )

        if not token:
            raise OAuthError("Failed to obtain access token", provider)

        return token


async def _process_oauth_user(
    oauth_providers: OAuth2Providers, provider: str, token: dict, db_session: DBSession, jwt_service: JWTService
):
    """Process OAuth user information and create session."""
    with span(
        "oauth.process_user",
        component="auth",
        operation="process_user",
        provider=provider,
    ):
        log_event(
            "oauth.user_info_request_start",
            component="auth",
            operation="get_user_info",
            provider=provider,
        )

        user_create = await oauth_providers.get_user_info(provider, token)

        log_event(
            "oauth.user_info_retrieved",
            component="auth",
            operation="get_user_info",
            provider=provider,
            has_email=bool(user_create and getattr(user_create, "email", None)),
            has_name=bool(user_create and getattr(user_create, "name", None)),
            user_email_domain=mask_text(getattr(user_create, "email", "").split("@")[-1])
            if user_create and getattr(user_create, "email", None)
            else None,
        )

        return _create_user_session(user_create, db_session, jwt_service)


def _create_user_session(user_create, db_session: DBSession, jwt_service: JWTService):
    """Create user and generate session tokens."""
    with span(
        "oauth.create_user_session",
        component="auth",
        operation="create_user_session",
    ):
        log_event(
            "oauth.user_registration_start",
            component="auth",
            operation="get_or_create_user",
        )

        registration_service = UserRegistrationService(db_session)
        user = registration_service.get_or_create_user(user_create)

        log_event(
            "oauth.user_registration_complete",
            component="auth",
            operation="get_or_create_user",
            user_id=user.id,
            user_email_masked=mask_text(user.email) if user.email else None,
        )

        log_event(
            "oauth.jwt_creation_start",
            component="auth",
            operation="create_token_pair",
            user_id=user.id,
        )

        user_service = UserService(db_session)
        token_data = jwt_service.create_token_pair(user.id, user.email)

        log_event(
            "oauth.jwt_creation_complete",
            component="auth",
            operation="create_token_pair",
            user_id=user.id,
            has_access_token=bool(token_data.get("access_token")),
            has_refresh_token=bool(token_data.get("refresh_token")),
            expires_in=token_data.get("expires_in"),
        )

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

    # Get client IP for security logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    with span(
        "oauth.login_initiate",
        component="auth",
        operation="oauth_login",
        provider=provider,
        client_ip=client_ip,
    ):
        log_event(
            "oauth.login_start",
            component="auth",
            operation="oauth_login",
            provider=provider,
            client_ip=client_ip,
            user_agent_masked=mask_text(user_agent),
        )

        try:
            oauth_client = oauth_providers.get_provider(provider)
            state = oauth_providers.generate_state()

            log_event(
                "oauth.state_generated",
                component="auth",
                operation="oauth_login",
                provider=provider,
                state_length=len(state),
                state_prefix=mask_text(state)[:8],
            )

            redirect_config = OAuthRedirectConfig()
            callback_url = redirect_config.build_callback_url(request, provider)

            log_event(
                "oauth.callback_url_built",
                component="auth",
                operation="oauth_login",
                provider=provider,
                callback_url_masked=mask_text(callback_url),
            )

            redirect_url = await oauth_client.authorize_redirect(request, callback_url, state=state)

            log_event(
                "oauth.login_redirect_success",
                component="auth",
                operation="oauth_login",
                provider=provider,
                client_ip=client_ip,
                redirect_url_masked=mask_text(str(redirect_url)),
            )

            return redirect_url

        except HTTPException as e:
            log_event(
                "oauth.login_http_error",
                level=logging.WARNING,
                component="auth",
                operation="oauth_login",
                provider=provider,
                client_ip=client_ip,
                error_type=type(e).__name__,
                status_code=e.status_code,
                error_detail=str(e.detail) if hasattr(e, "detail") else str(e),
            )
            raise
        except Exception as e:
            log_event(
                "oauth.login_error",
                level=logging.ERROR,
                component="auth",
                operation="oauth_login",
                provider=provider,
                client_ip=client_ip,
                error_type=type(e).__name__,
                error_msg=str(e),
            )
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
    cookie_config: Annotated[SessionCookieConfig, Depends(get_session_cookie_config)],
):
    """Handle OAuth callback and create user session."""
    rate_limit_middleware.check_oauth_rate_limit(request)
    provider = validate_provider_name(provider)

    # Get client IP for security logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    with span(
        "oauth.callback_flow",
        component="auth",
        operation="oauth_callback",
        provider=provider,
        client_ip=client_ip,
    ):
        log_event(
            "oauth.callback_start",
            component="auth",
            operation="oauth_callback",
            provider=provider,
            client_ip=client_ip,
            user_agent_masked=mask_text(user_agent),
            query_params_count=len(request.query_params),
        )

        try:
            oauth_client = oauth_providers.get_provider(provider)

            log_event(
                "oauth.provider_client_retrieved",
                component="auth",
                operation="oauth_callback",
                provider=provider,
            )

            _validate_oauth_callback(request, oauth_providers, provider)
            token = await _exchange_oauth_token(oauth_client, request, provider)
            result = await _process_oauth_user(oauth_providers, provider, token, db_session, jwt_service)

            log_event(
                "oauth.callback_success",
                component="auth",
                operation="oauth_callback",
                provider=provider,
                client_ip=client_ip,
                user_id=result.get("user").id if result.get("user") else None,
            )

            # Redirect to frontend with tokens in httpOnly cookies
            frontend_callback = f"http://localhost:3000/auth/callback/{provider}?success=true"

            log_event(
                "oauth.redirect_to_frontend",
                component="auth",
                operation="oauth_callback",
                provider=provider,
                frontend_url_masked=mask_text(frontend_callback),
            )

            response = RedirectResponse(url=frontend_callback)

            # Set httpOnly cookies with tokens
            cookie_settings = cookie_config.get_cookie_settings()

            # Set access token cookie (short-lived: 15 minutes)
            response.set_cookie(
                key="access_token",
                value=result["access_token"],
                max_age=jwt_service.access_token_expire_minutes * 60,
                httponly=True,
                secure=cookie_settings["secure"],
                samesite=cookie_settings["samesite"],
                path=cookie_settings["path"],
            )

            # Set refresh token cookie (long-lived: 30 days)
            response.set_cookie(
                key="refresh_token",
                value=result["refresh_token"],
                max_age=30 * 24 * 60 * 60,  # 30 days
                httponly=True,
                secure=cookie_settings["secure"],
                samesite=cookie_settings["samesite"],
                path=cookie_settings["path"],
            )

            log_event(
                "oauth.cookies_set",
                component="auth",
                operation="oauth_callback",
                provider=provider,
                has_access_token=True,
                has_refresh_token=True,
            )

            return response

        except HTTPException as e:
            db_session.rollback()
            log_event(
                "oauth.callback_http_error",
                level=logging.WARNING,
                component="auth",
                operation="oauth_callback",
                provider=provider,
                client_ip=client_ip,
                error_type=type(e).__name__,
                status_code=e.status_code,
                error_detail=str(e.detail) if hasattr(e, "detail") else str(e),
            )
            raise
        except Exception as e:
            db_session.rollback()
            log_event(
                "oauth.callback_error",
                level=logging.ERROR,
                component="auth",
                operation="oauth_callback",
                provider=provider,
                client_ip=client_ip,
                error_type=type(e).__name__,
                error_msg=str(e),
            )
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
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service_with_refresh)],
    cookie_config: Annotated[SessionCookieConfig, Depends(get_session_cookie_config)],
):
    """Refresh access token using refresh token from cookie."""
    rate_limit_middleware.check_refresh_token_rate_limit(request)

    try:
        # Read refresh token from cookie
        refresh_token_value = request.cookies.get("refresh_token")
        if not refresh_token_value:
            raise AuthenticationError("No refresh token found")

        refresh_token_service = RefreshTokenService(lambda: db_session)
        user_id = refresh_token_service.verify_refresh_token(refresh_token_value)

        if not user_id:
            raise AuthenticationError("Invalid or expired refresh token")

        # Get user info for new access token
        user_service = UserService(db_session)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise NotFoundError("User", user_id)

        # Create new access token
        access_token = jwt_service.create_access_token(user.id, user.email)

        # Return response with new access token cookie
        response = JSONResponse(
            content={
                "message": "Access token refreshed successfully",
                "token_type": "bearer",
                "expires_in": jwt_service.access_token_expire_minutes * 60,
            }
        )

        # Set new access token cookie
        cookie_settings = cookie_config.get_cookie_settings()
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=jwt_service.access_token_expire_minutes * 60,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise create_error_response(
            "token_refresh_failed", "Failed to refresh access token", status.HTTP_500_INTERNAL_SERVER_ERROR
        ) from e


@router.post("/logout")
async def logout(
    request: Request,
    refresh_token_service: Annotated[RefreshTokenService, Depends(get_refresh_token_service)],
    cookie_config: Annotated[SessionCookieConfig, Depends(get_session_cookie_config)],
):
    """Logout user and revoke refresh token."""
    try:
        # Read refresh token from cookie
        refresh_token_value = request.cookies.get("refresh_token")
        if refresh_token_value:
            refresh_token_service.revoke_refresh_token(refresh_token_value)

        # Create response
        response = JSONResponse(content={"message": "Logged out successfully"})

        # Clear cookies by setting max_age to 0
        cookie_settings = cookie_config.get_cookie_settings()

        response.set_cookie(
            key="access_token",
            value="",
            max_age=0,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        response.set_cookie(
            key="refresh_token",
            value="",
            max_age=0,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        return response

    except Exception:
        # Don't fail logout even if token revocation fails
        response = JSONResponse(content={"message": "Logged out successfully"})

        # Still try to clear cookies
        cookie_settings = cookie_config.get_cookie_settings()

        response.set_cookie(
            key="access_token",
            value="",
            max_age=0,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        response.set_cookie(
            key="refresh_token",
            value="",
            max_age=0,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        return response


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
