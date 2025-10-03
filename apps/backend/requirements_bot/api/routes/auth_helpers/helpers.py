"""Helper functions for authentication routes."""

from fastapi.responses import JSONResponse, RedirectResponse

from requirements_bot.api.auth import JWTService
from requirements_bot.api.error_responses import ValidationError
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig


def set_auth_cookies(
    response: JSONResponse | RedirectResponse,
    access_token: str,
    refresh_token: str | None,
    cookie_config: SessionCookieConfig,
    jwt_service: JWTService,
) -> None:
    """Set authentication cookies on response."""
    cookie_settings = cookie_config.get_cookie_settings()

    # Set access token cookie (short-lived: 15 minutes)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=jwt_service.access_token_expire_minutes * 60,
        httponly=True,
        secure=cookie_settings["secure"],
        samesite=cookie_settings["samesite"],
        path=cookie_settings["path"],
    )

    # Set refresh token cookie if provided (long-lived: 30 days)
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )


def clear_auth_cookies(response: JSONResponse, cookie_config: SessionCookieConfig) -> None:
    """Clear authentication cookies from response."""
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


def validate_provider_name(provider: str) -> str:
    """Validate OAuth provider name."""
    if not provider or not provider.strip():
        raise ValidationError("Provider name cannot be empty", "provider")

    provider = provider.strip().lower()
    if provider not in ["google", "github", "microsoft"]:
        raise ValidationError(f"Unsupported provider: {provider}", "provider")

    return provider
