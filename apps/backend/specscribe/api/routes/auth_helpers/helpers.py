"""Helper functions for authentication routes."""

from fastapi.responses import JSONResponse, RedirectResponse

from specscribe.api.auth import JWTService
from specscribe.api.error_responses import ValidationError
from specscribe.core.services.session_cookie_config import SessionCookieConfig
from specscribe.core.services.token_config import TokenConfig


def set_auth_cookies(
    response: JSONResponse | RedirectResponse,
    access_token: str,
    refresh_token: str | None,
    cookie_config: SessionCookieConfig,
    jwt_service: JWTService,
    token_config: TokenConfig | None = None,
) -> None:
    """Set authentication cookies on response."""
    if token_config is None:
        token_config = TokenConfig()

    cookie_settings = cookie_config.get_cookie_settings()

    # Set access token cookie (short-lived, configured via environment)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=jwt_service.access_token_expire_minutes * 60,
        httponly=True,
        secure=cookie_settings["secure"],
        samesite=cookie_settings["samesite"],
        path=cookie_settings["path"],
    )

    # Set refresh token cookie if provided (long-lived, configured via environment)
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=token_config.get_refresh_token_max_age_seconds(),
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
