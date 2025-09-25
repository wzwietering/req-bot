"""OAuth redirect URI configuration and validation service."""

import os
import re
from urllib.parse import urlparse

from fastapi import Request

from requirements_bot.api.error_responses import ValidationError


class OAuthRedirectConfig:
    """Manages OAuth redirect URI configuration and validation."""

    def __init__(self):
        self.allowed_domains = self._load_allowed_domains()
        self.base_callback_path = "/api/v1/auth/callback"

    def _load_allowed_domains(self) -> set[str]:
        """Load allowed redirect domains from environment."""
        domains_env = os.getenv("OAUTH_ALLOWED_DOMAINS", "")
        if not domains_env:
            # Default to localhost for development
            return {"localhost", "127.0.0.1"}

        # Split on both commas and semicolons to handle various formats
        domains = re.split(r"[,;]", domains_env)
        return {domain.strip().lower() for domain in domains if domain.strip()}

    def build_callback_url(self, request: Request, provider: str) -> str:
        """Build callback URL with domain validation."""
        base_url = self._get_base_url(request)
        self._validate_base_domain(base_url)

        return f"{base_url}{self.base_callback_path}/{provider}"

    def validate_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate if redirect URI is allowed."""
        try:
            parsed = urlparse(redirect_uri)

            # Reject URLs with userinfo (username:password@host) to prevent bypasses
            if "@" in redirect_uri:
                return False

            # Only allow http and https schemes
            if parsed.scheme not in ["http", "https"]:
                return False

            domain = parsed.netloc.lower()

            # Remove port for domain checking
            if ":" in domain:
                domain = domain.split(":")[0]

            return domain in self.allowed_domains
        except Exception:
            return False

    def _get_base_url(self, request: Request) -> str:
        """Extract base URL from request."""
        scheme = self._get_scheme(request)
        host = self._get_host(request)
        return f"{scheme}://{host}"

    def _get_scheme(self, request: Request) -> str:
        """Get URL scheme with proxy header support."""
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto and forwarded_proto.lower() in ["http", "https"]:
            return forwarded_proto.lower()
        return request.url.scheme or "https"

    def _get_host(self, request: Request) -> str:
        """Get host with proxy header support."""
        forwarded_host = request.headers.get("X-Forwarded-Host")
        if forwarded_host:
            return forwarded_host
        return request.headers.get("host", str(request.url.netloc))

    def _validate_base_domain(self, base_url: str) -> None:
        """Validate that base domain is allowed."""
        try:
            parsed = urlparse(base_url)
            domain = parsed.netloc.lower()

            # Check for empty/invalid netloc first
            if not domain:
                raise ValidationError("Invalid redirect URI format", "redirect_uri")

            if ":" in domain:
                domain = domain.split(":")[0]

            if domain not in self.allowed_domains:
                raise ValidationError(f"Domain {domain} not in allowed domains", "redirect_uri")
        except ValidationError:
            raise
        except Exception:
            raise ValidationError("Invalid redirect URI format", "redirect_uri")
