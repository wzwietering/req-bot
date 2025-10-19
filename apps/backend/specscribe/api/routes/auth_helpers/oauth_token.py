"""OAuth token exchange functions."""

import logging

import httpx
from fastapi import Request

from specscribe.api.auth import OAuth2Providers
from specscribe.api.error_responses import OAuthError
from specscribe.core.logging import log_event, span
from specscribe.core.services.oauth_redirect_config import OAuthRedirectConfig

logger = logging.getLogger(__name__)


async def exchange_oauth_token(oauth_client, request: Request, provider: str, oauth_providers: OAuth2Providers):
    """Exchange authorization code for OAuth token."""
    with span(
        "oauth.exchange_token",
        component="auth",
        operation="exchange_token",
        provider=provider,
    ):
        log_event(
            "oauth.token_exchange_start",
            level=logging.DEBUG,
            component="auth",
            operation="exchange_token",
            provider=provider,
        )

        # Microsoft requires manual token exchange to bypass ID token issuer validation
        # The /common/ endpoint returns tenant-specific issuer that doesn't match metadata
        if provider == "microsoft":
            token = await exchange_microsoft_token(request, oauth_providers)
        else:
            # Google and GitHub work fine with standard flow
            token = await oauth_client.authorize_access_token(request)

        has_access_token = bool(token and token.get("access_token"))
        has_token_type = bool(token and token.get("token_type"))

        log_event(
            "oauth.token_exchange_result",
            level=logging.DEBUG,
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


async def exchange_microsoft_token(request: Request, oauth_providers: OAuth2Providers) -> dict:
    """Manually exchange Microsoft authorization code for tokens.

    This bypasses Authlib's ID token validation which fails for /common/ endpoint
    due to tenant-specific issuer mismatch.
    """
    # Get authorization code from callback
    code = request.query_params.get("code")
    if not code:
        raise OAuthError("No authorization code in callback", "microsoft")

    # Get Microsoft OAuth config
    config = oauth_providers.get_provider_config("microsoft")

    # Build redirect URI
    redirect_config = OAuthRedirectConfig()
    redirect_uri = redirect_config.build_callback_url(request, "microsoft")

    # Manually exchange code for tokens
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": " ".join(config.scopes),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            logger.error(f"Microsoft token exchange failed: {response.status_code} {response.text}")
            raise OAuthError(f"Token exchange failed: {response.status_code}", "microsoft")

        token_data = response.json()

        # Validate token response structure
        if not token_data.get("access_token"):
            logger.error("Microsoft token response missing access_token")
            raise OAuthError("Invalid token response from Microsoft", "microsoft")

        token_type = token_data.get("token_type", "").lower()
        if token_type != "bearer":
            logger.error(f"Unexpected token type from Microsoft: {token_type}")
            raise OAuthError("Unexpected token type from Microsoft", "microsoft")

        # Return in format expected by rest of flow
        return {
            "access_token": token_data.get("access_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
        }
