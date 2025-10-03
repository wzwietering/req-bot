"""Token lifetime configuration service."""

import os

# Token lifetime defaults (in days for refresh tokens)
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

# Clock skew tolerance for token expiry validation (in seconds)
# Allows tolerance for time synchronization issues between servers
DEFAULT_CLOCK_SKEW_SECONDS = 30


class TokenConfig:
    """Manages token lifetime configuration from environment variables."""

    def __init__(self):
        self.refresh_token_expire_days = self._get_refresh_token_expire_days()
        self.access_token_expire_minutes = self._get_access_token_expire_minutes()
        self.clock_skew_seconds = self._get_clock_skew_seconds()

    def get_refresh_token_max_age_seconds(self) -> int:
        """Get refresh token max age in seconds for cookie configuration."""
        return self.refresh_token_expire_days * 24 * 60 * 60

    def _get_refresh_token_expire_days(self) -> int:
        """Get refresh token expiration in days from environment."""
        try:
            days_str = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", str(DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS))
            days = int(days_str)

            # Validate reasonable range: 1-90 days
            if days < 1:
                return DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS
            if days > 90:
                return DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

            return days
        except (ValueError, TypeError):
            return DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

    def _get_access_token_expire_minutes(self) -> int:
        """Get access token expiration in minutes from environment."""
        try:
            minutes_str = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES))
            minutes = int(minutes_str)

            # Validate reasonable range: 5-60 minutes
            if minutes < 5:
                return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
            if minutes > 60:
                return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

            return minutes
        except (ValueError, TypeError):
            return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

    def _get_clock_skew_seconds(self) -> int:
        """Get clock skew tolerance in seconds from environment."""
        try:
            seconds_str = os.getenv("CLOCK_SKEW_SECONDS", str(DEFAULT_CLOCK_SKEW_SECONDS))
            seconds = int(seconds_str)

            # Validate reasonable range: 0-300 seconds (5 minutes max)
            if seconds < 0:
                return DEFAULT_CLOCK_SKEW_SECONDS
            if seconds > 300:
                return DEFAULT_CLOCK_SKEW_SECONDS

            return seconds
        except (ValueError, TypeError):
            return DEFAULT_CLOCK_SKEW_SECONDS
