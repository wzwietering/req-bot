"""Unit tests for SessionCookieConfig service."""

import os
import threading
from unittest.mock import patch

from requirements_bot.core.services.session_cookie_config import SessionCookieConfig


class TestSessionCookieConfig:
    """Test session cookie configuration functionality."""

    def test_config_initialization_development(self):
        """Test configuration initialization in development environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = SessionCookieConfig()

            assert config.secure_cookies is False
            assert config.same_site_policy == "lax"
            assert config.max_age == 86400  # 24 hours
            assert config.domain is None

    def test_config_initialization_production(self):
        """Test configuration initialization in production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = SessionCookieConfig()

            assert config.secure_cookies is True
            assert config.same_site_policy == "lax"
            assert config.max_age == 86400
            assert config.domain is None

    def test_config_initialization_custom_settings(self):
        """Test configuration with custom environment settings."""
        custom_env = {
            "ENVIRONMENT": "production",
            "COOKIE_SAMESITE": "strict",
            "COOKIE_MAX_AGE": "3600",
            "COOKIE_DOMAIN": "example.com",
        }

        with patch.dict(os.environ, custom_env, clear=True):
            config = SessionCookieConfig()

            assert config.secure_cookies is True
            assert config.same_site_policy == "strict"
            assert config.max_age == 3600
            assert config.domain == "example.com"

    def test_get_cookie_settings_development(self):
        """Test cookie settings in development environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = SessionCookieConfig()

            settings = config.get_cookie_settings()

            expected = {
                "secure": False,
                "httponly": True,
                "samesite": "lax",
                "max_age": 86400,
                "domain": None,
                "path": "/",
            }

            assert settings == expected

    def test_get_cookie_settings_production(self):
        """Test cookie settings in production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = SessionCookieConfig()

            settings = config.get_cookie_settings()

            expected = {
                "secure": True,
                "httponly": True,
                "samesite": "lax",
                "max_age": 86400,
                "domain": None,
                "path": "/",
            }

            assert settings == expected

    def test_get_response_headers_development(self):
        """Test response headers in development environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = SessionCookieConfig()

            headers = config.get_response_headers(for_docs=False)

            expected = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            }

            assert headers == expected
            assert "Strict-Transport-Security" not in headers

    def test_get_response_headers_production(self):
        """Test response headers in production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            config = SessionCookieConfig()

            headers = config.get_response_headers(for_docs=False)

            expected = {
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Content-Security-Policy": "default-src 'self'",
                "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            }

            assert headers == expected

    def test_get_response_headers_for_docs(self):
        """Test response headers with relaxed CSP for API documentation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            config = SessionCookieConfig()

            headers = config.get_response_headers(for_docs=True)

            # Check all standard headers are present
            assert headers["X-Content-Type-Options"] == "nosniff"
            assert headers["X-Frame-Options"] == "DENY"
            assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
            assert headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"

            # Check relaxed CSP for docs
            csp = headers["Content-Security-Policy"]
            assert "default-src 'self'" in csp
            assert "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net" in csp
            assert "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net" in csp
            assert "img-src 'self' data: fastapi.tiangolo.com" in csp

    def test_is_production_environment_detection(self):
        """Test production environment detection."""
        config = SessionCookieConfig()

        production_envs = ["production", "prod", "live", "PRODUCTION", "PROD", "LIVE"]
        for env in production_envs:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                assert config._is_production() is True

        development_envs = ["development", "dev", "test", "staging", "local", ""]
        for env in development_envs:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                assert config._is_production() is False

    def test_get_same_site_policy_valid_values(self):
        """Test SameSite policy validation with valid values."""
        config = SessionCookieConfig()

        valid_policies = ["strict", "lax", "none", "STRICT", "LAX", "NONE"]
        for policy in valid_policies:
            with patch.dict(os.environ, {"COOKIE_SAMESITE": policy}):
                result = config._get_same_site_policy()
                assert result == policy.lower()

    def test_get_same_site_policy_invalid_values(self):
        """Test SameSite policy defaults with invalid values."""
        config = SessionCookieConfig()

        invalid_policies = ["invalid", "secure", "true", "false", ""]
        for policy in invalid_policies:
            with patch.dict(os.environ, {"COOKIE_SAMESITE": policy}):
                result = config._get_same_site_policy()
                assert result == "lax"  # Default fallback

    def test_get_max_age_valid_values(self):
        """Test max age parsing with valid values."""
        config = SessionCookieConfig()

        valid_ages = ["3600", "86400", "604800", "0"]
        for age in valid_ages:
            with patch.dict(os.environ, {"COOKIE_MAX_AGE": age}):
                result = config._get_max_age()
                assert result == int(age)

    def test_get_max_age_invalid_values(self):
        """Test max age defaults with invalid values."""
        config = SessionCookieConfig()

        invalid_ages = ["invalid", "3600.5", "-1", "abc", ""]
        for age in invalid_ages:
            with patch.dict(os.environ, {"COOKIE_MAX_AGE": age}):
                result = config._get_max_age()
                assert result == 86400  # Default fallback

    def test_get_domain_valid_values(self):
        """Test domain setting with valid values."""
        config = SessionCookieConfig()

        valid_domains = ["example.com", ".example.com", "app.example.com"]
        for domain in valid_domains:
            with patch.dict(os.environ, {"COOKIE_DOMAIN": domain}):
                result = config._get_domain()
                assert result == domain

    def test_get_domain_empty_values(self):
        """Test domain setting with empty values."""
        config = SessionCookieConfig()

        empty_values = ["", "   ", "\t", "\n"]
        for domain in empty_values:
            with patch.dict(os.environ, {"COOKIE_DOMAIN": domain}):
                result = config._get_domain()
                assert result is None


class TestSessionCookieConfigSecurity:
    """Test security-specific scenarios for session cookie configuration."""

    def test_secure_flag_enforced_in_production(self):
        """Test that secure flag is enforced in production."""
        production_envs = ["production", "prod", "live"]

        for env in production_envs:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                config = SessionCookieConfig()
                settings = config.get_cookie_settings()

                assert settings["secure"] is True, f"Secure flag should be True in {env}"

    def test_httponly_flag_always_enabled(self):
        """Test that HttpOnly flag is always enabled for security."""
        environments = ["development", "production", "test", "staging"]

        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                config = SessionCookieConfig()
                settings = config.get_cookie_settings()

                assert settings["httponly"] is True, f"HttpOnly should always be True in {env}"

    def test_hsts_header_production_only(self):
        """Test that HSTS header is only set in production."""
        # Development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            config = SessionCookieConfig()
            headers = config.get_response_headers()

            assert "Strict-Transport-Security" not in headers

        # Production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = SessionCookieConfig()
            headers = config.get_response_headers()

            assert "Strict-Transport-Security" in headers
            assert "max-age=31536000; includeSubDomains" in headers["Strict-Transport-Security"]

    def test_security_headers_always_present(self):
        """Test that security headers are always present."""
        environments = ["development", "production", "test"]

        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                config = SessionCookieConfig()
                headers = config.get_response_headers(for_docs=False)

                # These headers should always be present
                assert headers["X-Content-Type-Options"] == "nosniff"
                assert headers["X-Frame-Options"] == "DENY"
                assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
                assert headers["Content-Security-Policy"] == "default-src 'self'"
                assert headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"

    def test_samesite_none_requires_secure_context(self):
        """Test that SameSite=None is handled appropriately."""
        # In development with SameSite=None
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "COOKIE_SAMESITE": "none"}):
            config = SessionCookieConfig()
            settings = config.get_cookie_settings()

            # SameSite=None requires Secure=True, but we're in development
            assert settings["samesite"] == "none"
            assert settings["secure"] is False  # Development override

        # In production with SameSite=None
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "COOKIE_SAMESITE": "none"}):
            config = SessionCookieConfig()
            settings = config.get_cookie_settings()

            assert settings["samesite"] == "none"
            assert settings["secure"] is True  # Required for SameSite=None

    def test_cookie_domain_security_validation(self):
        """Test that cookie domain setting handles potentially dangerous values."""
        # Test non-null-byte dangerous values
        dangerous_domains = [
            "<script>alert('xss')</script>",
            "evil.com\r\nSet-Cookie: malicious=1",
            "domain'; DROP TABLE sessions; --",
        ]

        for dangerous_domain in dangerous_domains:
            with patch.dict(os.environ, {"COOKIE_DOMAIN": dangerous_domain}):
                config = SessionCookieConfig()
                # Should either sanitize or use the value as-is (validation happens elsewhere)
                domain = config._get_domain()
                # The important thing is it doesn't crash
                assert isinstance(domain, (str, type(None)))

        # Test null byte handling separately (Python environ doesn't allow null bytes)
        # We test this by directly calling the sanitization method
        config = SessionCookieConfig()
        null_byte_domain = config._sanitize_env_value("\x00null-byte.com")
        assert null_byte_domain == "null-byte.com"  # Null byte should be stripped

    def test_max_age_bounds_checking(self):
        """Test that max age values are within reasonable bounds."""
        extreme_values = [
            "999999999999999999",  # Very large number
            "-999999999",  # Negative number
            "0",  # Zero (valid but short)
        ]

        for value in extreme_values:
            with patch.dict(os.environ, {"COOKIE_MAX_AGE": value}):
                config = SessionCookieConfig()
                try:
                    max_age = config._get_max_age()
                    # Should either parse the value or use default
                    assert isinstance(max_age, int)
                    assert max_age >= 0  # Should not be negative
                except (ValueError, OverflowError):
                    # Acceptable to reject extreme values
                    pass

    def test_environment_variable_injection_protection(self):
        """Test protection against environment variable injection."""
        # Test CRLF injection (without null bytes which Python environ rejects)
        malicious_env_values = {
            "ENVIRONMENT": "production\r\ninjected: value",
            "COOKIE_DOMAIN": "example.com\r\nInjected-Header: malicious",
        }

        with patch.dict(os.environ, malicious_env_values):
            config = SessionCookieConfig()

            # Should handle malicious input gracefully
            settings = config.get_cookie_settings()
            headers = config.get_response_headers(for_docs=False)

            # Verify no injection occurred in cookie settings
            for value in settings.values():
                if isinstance(value, str):
                    assert "\r" not in value
                    assert "\n" not in value

            # Verify no injection in headers
            for header_value in headers.values():
                assert "\r" not in header_value
                assert "\n" not in header_value

        # Test null byte sanitization directly (Python environ doesn't allow null bytes)
        config = SessionCookieConfig()
        null_byte_samesite = config._sanitize_env_value("lax\x00admin")
        assert null_byte_samesite == "laxadmin"  # Null byte should be stripped
        assert "\x00" not in null_byte_samesite

    def test_cookie_path_security(self):
        """Test that cookie path is securely configured."""
        config = SessionCookieConfig()
        settings = config.get_cookie_settings()

        # Path should be root to prevent cookie scoping attacks
        assert settings["path"] == "/"

    def test_production_detection_case_insensitive(self):
        """Test that production detection is case-insensitive."""
        case_variations = [
            ("production", True),
            ("PRODUCTION", True),
            ("Production", True),
            ("prod", True),
            ("PROD", True),
            ("live", True),
            ("LIVE", True),
            ("development", False),
            ("test", False),
            ("staging", False),
            ("", False),
        ]

        for env_value, expected in case_variations:
            with patch.dict(os.environ, {"ENVIRONMENT": env_value}):
                config = SessionCookieConfig()
                assert config._is_production() == expected

    def test_concurrent_configuration_access(self):
        """Test that configuration can be safely accessed concurrently."""
        results = []
        errors = []

        def access_config():
            try:
                with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                    config = SessionCookieConfig()
                    settings = config.get_cookie_settings()
                    headers = config.get_response_headers(for_docs=False)
                    results.append((settings, headers))
            except Exception as e:
                errors.append(e)

        # Create multiple threads accessing configuration
        threads = [threading.Thread(target=access_config) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have any errors and all results should be consistent
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"
        assert len(results) == 10

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result

    def test_configuration_immutability(self):
        """Test that configuration objects maintain consistent state."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            config = SessionCookieConfig()

            # Get initial values
            initial_settings = config.get_cookie_settings()
            initial_headers = config.get_response_headers(for_docs=False)

            # Try to modify returned dicts (should not affect config)
            initial_settings["secure"] = False
            initial_headers["X-Frame-Options"] = "ALLOW-FROM evil.com"

            # Get values again - should be unchanged
            new_settings = config.get_cookie_settings()
            new_headers = config.get_response_headers(for_docs=False)

            assert new_settings["secure"] is True
            assert new_headers["X-Frame-Options"] == "DENY"
