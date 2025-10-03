import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
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
    create_error_response,
)
from requirements_bot.api.rate_limiting import rate_limit_middleware
from requirements_bot.api.routes.auth_helpers import (
    clear_auth_cookies,
    exchange_oauth_token,
    process_oauth_user,
    set_auth_cookies,
    validate_oauth_callback,
    validate_provider_name,
)
from requirements_bot.core.logging import audit_log, log_event, mask_text, span
from requirements_bot.core.models import UserResponse
from requirements_bot.core.services.oauth_redirect_config import OAuthRedirectConfig
from requirements_bot.core.services.refresh_token_service import RefreshTokenService
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig
from requirements_bot.core.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


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
            level=logging.DEBUG,
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
                level=logging.DEBUG,
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
                level=logging.DEBUG,
                component="auth",
                operation="oauth_login",
                provider=provider,
                callback_url_masked=mask_text(callback_url),
            )

            redirect_url = await oauth_client.authorize_redirect(request, callback_url, state=state)

            log_event(
                "oauth.login_redirect_success",
                level=logging.INFO,
                component="auth",
                operation="oauth_login",
                provider=provider,
                client_ip=client_ip,
                redirect_url_masked=mask_text(str(redirect_url)),
            )

            return redirect_url

        except HTTPException:
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
            level=logging.DEBUG,
            component="auth",
            operation="oauth_callback",
            provider=provider,
            client_ip=client_ip,
            user_agent_masked=mask_text(user_agent),
            query_params_count=len(request.query_params),
        )

        try:
            oauth_client = oauth_providers.get_provider(provider)

            validate_oauth_callback(request, oauth_providers, provider)
            token = await exchange_oauth_token(oauth_client, request, provider, oauth_providers)
            result = await process_oauth_user(oauth_providers, provider, token, db_session, jwt_service)

            log_event(
                "oauth.callback_success",
                level=logging.INFO,
                component="auth",
                operation="oauth_callback",
                provider=provider,
                client_ip=client_ip,
                user_id=result.get("user").id if result.get("user") else None,
            )

            # Redirect to frontend with tokens in httpOnly cookies
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            frontend_callback = f"{frontend_url}/auth/callback/{provider}?success=true"

            response = RedirectResponse(url=frontend_callback)

            # Set httpOnly cookies with tokens
            set_auth_cookies(
                response,
                result["access_token"],
                result["refresh_token"],
                cookie_config,
                jwt_service,
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
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
            # Audit log for failed authentication
            audit_log(
                "oauth.authentication_failed",
                user_id=None,
                client_ip=client_ip,
                provider=provider,
                error_type=type(e).__name__,
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
    """Refresh access token using refresh token from cookie with token rotation."""
    rate_limit_middleware.check_refresh_token_rate_limit(request)

    client_ip = request.client.host if request.client else "unknown"

    try:
        # Read refresh token from cookie
        old_refresh_token = request.cookies.get("refresh_token")
        if not old_refresh_token:
            # Audit log for missing refresh token
            audit_log(
                "token.refresh_failed_no_token",
                user_id=None,
                client_ip=client_ip,
                reason="No refresh token found in request",
            )
            raise AuthenticationError("No refresh token found")

        refresh_token_service = RefreshTokenService(lambda: db_session)

        # Rotate refresh token (revoke old, issue new)
        rotation_result = refresh_token_service.refresh_and_rotate(old_refresh_token)

        if not rotation_result:
            # Audit log for failed token refresh (could be replay attack)
            audit_log(
                "token.refresh_failed_invalid",
                user_id=None,
                client_ip=client_ip,
                reason="Invalid or expired refresh token",
            )
            raise AuthenticationError("Invalid or expired refresh token")

        user_id, new_refresh_token = rotation_result

        # Get user info for new access token
        user_service = UserService(db_session)
        user = user_service.get_user_by_id(user_id)

        if not user:
            raise NotFoundError("User", user_id)

        # Create new access token
        access_token = jwt_service.create_access_token(user.id, user.email)

        log_event(
            "auth.token_refresh_success",
            level=logging.INFO,
            component="auth",
            operation="refresh_token",
            user_id=user.id,
            rotated_refresh_token=True,
        )

        # Audit log for successful token refresh
        audit_log(
            "token.refresh_success",
            user_id=user.id,
            client_ip=client_ip,
        )

        # Return response with new tokens in cookies
        response = JSONResponse(
            content={
                "message": "Tokens refreshed successfully",
                "token_type": "bearer",
                "expires_in": jwt_service.access_token_expire_minutes * 60,
            }
        )

        # Set both access and new refresh token cookies
        set_auth_cookies(response, access_token, new_refresh_token, cookie_config, jwt_service)

        return response

    except HTTPException:
        raise
    except Exception as e:
        log_event(
            "auth.token_refresh_failed",
            level=logging.ERROR,
            component="auth",
            operation="refresh_token",
            error_type=type(e).__name__,
            error_msg=str(e),
        )
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

        # Clear cookies
        clear_auth_cookies(response, cookie_config)

        return response

    except Exception as e:
        # Don't fail logout even if token revocation fails
        log_event(
            "auth.logout_token_revocation_failed",
            level=logging.ERROR,
            component="auth",
            operation="logout",
            error_type=type(e).__name__,
            error_msg=str(e),
        )

        response = JSONResponse(content={"message": "Logged out successfully"})

        # Still clear cookies for user experience
        clear_auth_cookies(response, cookie_config)

        return response


@router.post("/invalidate-sessions")
async def invalidate_user_sessions(
    request: Request,
    db_session: Annotated[DBSession, Depends(get_database_session)],
    refresh_token_service: Annotated[RefreshTokenService, Depends(get_refresh_token_service)],
):
    """Invalidate all sessions for the current user.

    Useful for security events like password changes, suspicious activity detection,
    or when user wants to log out from all devices.
    """
    # Get current user from authentication middleware
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthenticationError()

    client_ip = request.client.host if request.client else "unknown"

    try:
        # Revoke all refresh tokens for the user
        revoked_count = refresh_token_service.revoke_all_user_tokens(user_id)

        log_event(
            "auth.sessions_invalidated",
            level=logging.INFO,
            component="auth",
            operation="invalidate_sessions",
            user_id=user_id,
            tokens_revoked=revoked_count,
        )

        # Audit log for session invalidation (security event)
        audit_log(
            "sessions.invalidated_all",
            user_id=user_id,
            client_ip=client_ip,
            sessions_revoked=revoked_count,
        )

        return JSONResponse(
            content={
                "message": "All sessions invalidated successfully",
                "sessions_revoked": revoked_count,
            }
        )

    except Exception as e:
        log_event(
            "auth.session_invalidation_failed",
            level=logging.ERROR,
            component="auth",
            operation="invalidate_sessions",
            user_id=user_id,
            error_type=type(e).__name__,
            error_msg=str(e),
        )
        raise create_error_response(
            "session_invalidation_failed",
            "Failed to invalidate sessions",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from e


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
