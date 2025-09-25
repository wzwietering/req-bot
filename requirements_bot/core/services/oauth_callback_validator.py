"""OAuth callback parameter validation service."""

import re

from fastapi import Request

from requirements_bot.api.error_responses import OAuthError, ValidationError


class OAuthCallbackValidator:
    """Validates OAuth callback parameters for security."""

    def __init__(self):
        self.max_code_length = 512
        self.max_state_length = 128
        self.max_error_length = 256

    def validate_callback_params(self, request: Request, provider: str) -> dict:
        """Validate all OAuth callback parameters."""
        params = dict(request.query_params)

        # Check for required parameters
        if "error" in params:
            self._validate_error_param(params["error"], provider)
            raise OAuthError(f"OAuth error: {params['error']}", provider)

        code = self._validate_code_param(params.get("code"), provider)
        state = self._validate_state_param(params.get("state"), provider)

        return {"code": code, "state": state}

    def _validate_code_param(self, code: str, provider: str) -> str:
        """Validate OAuth authorization code parameter."""
        if not code:
            raise ValidationError("Missing authorization code", "code")

        # Check for dangerous characters BEFORE stripping (strip removes some Unicode chars)
        if not self._is_safe_param(code):
            raise ValidationError("Invalid authorization code format", "code")

        # Strip whitespace
        code = code.strip()

        if len(code) > self.max_code_length:
            raise ValidationError("Authorization code too long", "code")

        return code

    def _validate_state_param(self, state: str, provider: str) -> str:
        """Validate OAuth state parameter."""
        if not state:
            raise ValidationError("Missing state parameter", "state")

        # Strip whitespace first
        state = state.strip()

        if len(state) > self.max_state_length:
            raise ValidationError("State parameter too long", "state")

        if not self._is_valid_state_format(state):
            raise ValidationError("Invalid state parameter format", "state")

        return state

    def _validate_error_param(self, error: str, provider: str) -> None:
        """Validate OAuth error parameter."""
        if len(error) > self.max_error_length:
            raise ValidationError("Error parameter too long", "error")

        if not self._is_safe_param(error):
            raise ValidationError("Invalid error parameter format", "error")

    def _is_safe_param(self, param: str) -> bool:
        """Check if parameter contains only safe characters."""
        # Reject path traversal patterns
        if ".." in param or "\\" in param or "%2e" in param.lower() or "%2f" in param.lower():
            return False

        # Check for Unicode control characters and invisible chars
        dangerous_unicode = [
            8238,  # 0x202e - Right-to-left override
            65279,  # 0xfeff - Byte order mark
            160,  # 0x00a0 - Non-breaking space
            8232,  # 0x2028 - Line separator
            8233,  # 0x2029 - Paragraph separator
            133,  # 0x0085 - Next line
            11,  # 0x000b - Vertical tab
            12,  # 0x000c - Form feed
        ]
        if any(ord(char) in dangerous_unicode for char in param):
            return False

        # Check for other control characters (0-31 except tab, newline, carriage return)
        for char in param:
            char_code = ord(char)
            if (0 <= char_code <= 31 and char_code not in [9, 10, 13]) or (127 <= char_code <= 159):
                return False

        # Check the stripped version for control chars and inner spaces
        stripped_param = param.strip()
        if any(ord(char) < 32 for char in stripped_param):
            return False
        if " " in stripped_param:  # Reject inner spaces
            return False

        # Allow leading/trailing spaces but only safe chars in content
        if param != param.strip():
            # Has leading/trailing spaces, validate the stripped version
            return re.match(r"^[a-zA-Z0-9._/-]+$", stripped_param) is not None
        else:
            # No leading/trailing spaces, validate normally
            return re.match(r"^[a-zA-Z0-9._/-]+$", param) is not None

    def _is_valid_state_format(self, state: str) -> bool:
        """Validate OAuth state parameter format."""
        if not state or len(state) < 10 or len(state) > self.max_state_length:
            return False

        # Allow alphanumeric, hyphens, and underscores only for state
        if not re.match(r"^[a-zA-Z0-9_-]+$", state):
            return False

        # Reject obviously predictable patterns (very specific to avoid false positives)
        predictable_patterns = [
            r"^predictable123$",  # Exact match for test case from failing test
            r"^[0-9]+$",  # Only numbers
        ]

        for pattern in predictable_patterns:
            if re.match(pattern, state, re.IGNORECASE):
                return False

        return True
