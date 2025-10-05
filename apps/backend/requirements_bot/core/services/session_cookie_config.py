"""Session cookie security configuration service."""

import os
from typing import Any


class SessionCookieConfig:
    """Manages secure session cookie configuration."""

    def __init__(self):
        self.secure_cookies = self._is_production()
        self.same_site_policy = self._get_same_site_policy()
        self.max_age = self._get_max_age()
        self.domain = self._get_domain()

    def get_cookie_settings(self) -> dict[str, Any]:
        """Get complete cookie security settings."""
        return {
            "secure": self.secure_cookies,
            "httponly": True,
            "samesite": self.same_site_policy,
            "max_age": self.max_age,
            "domain": self.domain,
            "path": "/",
        }

    def get_response_headers(self, for_docs: bool = False) -> dict[str, str]:
        """Get comprehensive security headers for cookie responses.

        Args:
            for_docs: If True, uses relaxed CSP for API documentation endpoints
        """
        headers = {}

        # HSTS - Force HTTPS for 1 year in production
        if self.secure_cookies:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Prevent MIME type sniffing
        headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        headers["X-Frame-Options"] = "DENY"

        # Referrer policy - Don't leak full URL to external sites
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - Restrict resource loading
        if for_docs:
            # Relaxed CSP for API docs to allow Swagger UI resources
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data: fastapi.tiangolo.com"
            )
        else:
            # Strict CSP for all other routes
            headers["Content-Security-Policy"] = "default-src 'self'"

        # Permissions Policy - Disable unnecessary browser features
        headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return headers

    def _is_production(self) -> bool:
        """Check if running in production environment."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        return env in ["production", "prod", "live"]

    def _get_same_site_policy(self) -> str:
        """Get SameSite policy from environment."""
        policy_raw = os.getenv("COOKIE_SAMESITE", "lax")
        policy_sanitized = self._sanitize_env_value(policy_raw)

        if policy_sanitized:
            policy = policy_sanitized.lower()
            if policy in ["strict", "lax", "none"]:
                return policy

        return "lax"

    def _get_max_age(self) -> int:
        """Get cookie max age in seconds."""
        try:
            max_age_str = os.getenv("COOKIE_MAX_AGE", "86400")
            max_age = int(max_age_str)

            # Reject negative values and use default
            if max_age < 0:
                return 86400

            return max_age
        except (ValueError, TypeError, OverflowError):
            return 86400

    def _sanitize_env_value(self, value: str | None) -> str | None:
        """Sanitize environment variable value to prevent injection attacks."""
        if not value:
            return None

        try:
            # Remove null bytes and CRLF characters that could cause injection
            sanitized = value.replace("\x00", "").replace("\r", "").replace("\n", "").strip()
            return sanitized if sanitized else None
        except (AttributeError, TypeError):
            return None

    def _get_domain(self) -> str | None:
        """Get cookie domain from environment."""
        domain = os.getenv("COOKIE_DOMAIN", "")
        return self._sanitize_env_value(domain)
