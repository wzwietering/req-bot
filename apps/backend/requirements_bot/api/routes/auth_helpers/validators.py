"""OAuth validation functions."""

import logging

from fastapi import Request

from requirements_bot.api.auth import OAuth2Providers
from requirements_bot.api.error_responses import OAuthError
from requirements_bot.core.logging import log_event, mask_text, span
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator

logger = logging.getLogger(__name__)


def validate_oauth_callback(request: Request, oauth_providers: OAuth2Providers, provider: str) -> dict:
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
