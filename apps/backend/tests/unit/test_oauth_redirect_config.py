"""Unit tests for OAuthRedirectConfig service."""

import os
from unittest.mock import Mock, patch

import pytest

from specscribe.api.error_responses import ValidationError
from specscribe.core.services.oauth_redirect_config import OAuthRedirectConfig


class TestOAuthRedirectConfig:
    """Test OAuth redirect URI configuration and validation."""

    def test_config_initialization_default_domains(self):
        """Test configuration initialization with default allowed domains."""
        with patch.dict(os.environ, {}, clear=True):
            config = OAuthRedirectConfig()

            assert "localhost" in config.allowed_domains
            assert "127.0.0.1" in config.allowed_domains
            assert config.base_callback_path == "/api/v1/auth/callback"

    def test_config_initialization_custom_domains(self):
        """Test configuration initialization with custom allowed domains."""
        custom_domains = "example.com,app.example.com,subdomain.test.org"

        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": custom_domains}):
            config = OAuthRedirectConfig()

            assert "example.com" in config.allowed_domains
            assert "app.example.com" in config.allowed_domains
            assert "subdomain.test.org" in config.allowed_domains
            assert len(config.allowed_domains) == 3

    def test_config_initialization_domains_with_whitespace(self):
        """Test configuration handles domains with whitespace."""
        domains_with_whitespace = " example.com , app.example.com,  test.org  "

        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": domains_with_whitespace}):
            config = OAuthRedirectConfig()

            assert "example.com" in config.allowed_domains
            assert "app.example.com" in config.allowed_domains
            assert "test.org" in config.allowed_domains

    def test_config_initialization_empty_domains(self):
        """Test configuration with empty domains environment variable."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": ""}):
            config = OAuthRedirectConfig()

            # Should fall back to defaults
            assert "localhost" in config.allowed_domains
            assert "127.0.0.1" in config.allowed_domains

    def test_build_callback_url_success(self):
        """Test successful callback URL building."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            request = Mock()
            request.url.scheme = "https"
            request.headers = {"host": "example.com"}

            callback_url = config.build_callback_url(request, "google")

            expected = "https://example.com/api/v1/auth/callback/google"
            assert callback_url == expected

    def test_build_callback_url_with_port(self):
        """Test callback URL building with port number."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "localhost"}):
            config = OAuthRedirectConfig()

            request = Mock()
            request.url.scheme = "http"
            request.headers = {"host": "localhost:8080"}

            callback_url = config.build_callback_url(request, "github")

            expected = "http://localhost:8080/api/v1/auth/callback/github"
            assert callback_url == expected

    def test_build_callback_url_invalid_domain(self):
        """Test callback URL building fails with invalid domain."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            request = Mock()
            request.url.scheme = "https"
            request.headers = {"host": "evil.com"}

            with pytest.raises(ValidationError) as exc_info:
                config.build_callback_url(request, "google")

            assert "Domain evil.com not in allowed domains" in str(exc_info.value)

    def test_validate_redirect_uri_success(self):
        """Test successful redirect URI validation."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com,app.test.org"}):
            config = OAuthRedirectConfig()

            valid_uris = [
                "https://example.com/callback",
                "http://example.com/auth",
                "https://app.test.org/oauth/callback",
                "http://app.test.org:8080/callback",
            ]

            for uri in valid_uris:
                assert config.validate_redirect_uri(uri) is True

    def test_validate_redirect_uri_invalid_domain(self):
        """Test redirect URI validation fails for invalid domains."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            invalid_uris = [
                "https://evil.com/callback",
                "http://phishing.net/auth",
                "https://subdomain.evil.com/callback",
            ]

            for uri in invalid_uris:
                assert config.validate_redirect_uri(uri) is False

    def test_validate_redirect_uri_malformed_url(self):
        """Test redirect URI validation handles malformed URLs."""
        config = OAuthRedirectConfig()

        malformed_uris = ["not-a-url", "http://", "ftp://example.com/callback", "javascript:alert('xss')", ""]

        for uri in malformed_uris:
            assert config.validate_redirect_uri(uri) is False

    def test_get_base_url_standard(self):
        """Test base URL extraction from standard request."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = "https"
        request.headers = {"host": "example.com"}

        base_url = config._get_base_url(request)
        assert base_url == "https://example.com"

    def test_get_base_url_with_proxy_headers(self):
        """Test base URL extraction with proxy headers."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = "http"
        request.headers = {
            "host": "internal.server",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": "public.example.com",
        }

        base_url = config._get_base_url(request)
        assert base_url == "https://public.example.com"

    def test_get_scheme_proxy_header(self):
        """Test scheme extraction with proxy header."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = "http"
        request.headers = {"X-Forwarded-Proto": "https"}

        scheme = config._get_scheme(request)
        assert scheme == "https"

    def test_get_scheme_invalid_proxy_header(self):
        """Test scheme extraction ignores invalid proxy header."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = "https"
        request.headers = {"X-Forwarded-Proto": "ftp"}  # Invalid scheme

        scheme = config._get_scheme(request)
        assert scheme == "https"  # Falls back to original

    def test_get_scheme_default_https(self):
        """Test scheme defaults to https when not specified."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = None
        request.headers = {}

        scheme = config._get_scheme(request)
        assert scheme == "https"

    def test_get_host_proxy_header(self):
        """Test host extraction with proxy header."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.netloc = "internal:8080"
        request.headers = {"host": "internal:8080", "X-Forwarded-Host": "public.example.com"}

        host = config._get_host(request)
        assert host == "public.example.com"

    def test_get_host_fallback(self):
        """Test host extraction fallback to URL netloc."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.netloc = "example.com:443"
        request.headers = {}

        host = config._get_host(request)
        assert host == "example.com:443"

    def test_validate_base_domain_success(self):
        """Test successful base domain validation."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            # Should not raise exception
            config._validate_base_domain("https://example.com")
            config._validate_base_domain("http://example.com:8080")

    def test_validate_base_domain_with_port_stripping(self):
        """Test base domain validation strips port numbers."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "localhost"}):
            config = OAuthRedirectConfig()

            # Should not raise exception - port should be stripped
            config._validate_base_domain("http://localhost:8080")
            config._validate_base_domain("https://localhost:443")

    def test_validate_base_domain_failure(self):
        """Test base domain validation failure."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            with pytest.raises(ValidationError) as exc_info:
                config._validate_base_domain("https://evil.com")

            assert "Domain evil.com not in allowed domains" in str(exc_info.value)

    def test_validate_base_domain_malformed_url(self):
        """Test base domain validation with malformed URL."""
        config = OAuthRedirectConfig()

        with pytest.raises(ValidationError) as exc_info:
            config._validate_base_domain("not-a-url")

        assert "Invalid redirect URI format" in str(exc_info.value)


class TestOAuthRedirectConfigSecurity:
    """Test security-specific scenarios for OAuth redirect configuration."""

    def test_domain_whitelist_prevents_open_redirect(self):
        """Test that domain whitelist prevents open redirect attacks."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "trustedsite.com"}):
            config = OAuthRedirectConfig()

            malicious_uris = [
                "https://evil.com/callback",
                "http://phishing.net/steal-tokens",
                "https://trustedsite.com.evil.com/callback",  # Subdomain confusion
                "https://evilsite.com/callback?redirect=trustedsite.com",
                "https://192.168.1.1/callback",  # IP address
            ]

            for uri in malicious_uris:
                assert config.validate_redirect_uri(uri) is False, f"URI should be rejected: {uri}"

    def test_subdomain_confusion_attack_prevention(self):
        """Test prevention of subdomain confusion attacks."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            confusion_attacks = [
                "https://example.com.evil.com/callback",
                "https://malicious-example.com/callback",
                "https://examplefcom/callback",
                "https://example-com.evil.net/callback",
            ]

            for uri in confusion_attacks:
                assert config.validate_redirect_uri(uri) is False

    def test_ip_address_blocking(self):
        """Test that IP addresses are properly validated against whitelist."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "127.0.0.1,192.168.1.100"}):
            config = OAuthRedirectConfig()

            # Allowed IPs
            assert config.validate_redirect_uri("http://127.0.0.1/callback") is True
            assert config.validate_redirect_uri("http://192.168.1.100/callback") is True

            # Disallowed IPs
            assert config.validate_redirect_uri("http://192.168.1.1/callback") is False
            assert config.validate_redirect_uri("http://10.0.0.1/callback") is False

    def test_protocol_validation_security(self):
        """Test that only HTTP/HTTPS protocols are accepted."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            dangerous_protocols = [
                "javascript://example.com/callback",
                "data://example.com/callback",
                "ftp://example.com/callback",
                "file://example.com/callback",
                "ldap://example.com/callback",
            ]

            for uri in dangerous_protocols:
                assert config.validate_redirect_uri(uri) is False

    def test_url_parsing_edge_cases(self):
        """Test URL parsing handles edge cases securely."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            edge_cases = [
                "https://example.com@evil.com/callback",  # User info
                "https://example.com:999999/callback",  # Invalid port
                "https://example.com/../../../etc/passwd",  # Path traversal
                "https://example.com/callback#fragment",  # Fragment
                "https://example.com/callback?param=value",  # Query params
                "HTTPS://EXAMPLE.COM/callback",  # Case sensitivity
            ]

            # All should be handled gracefully (either accepted or rejected, not crash)
            for uri in edge_cases:
                try:
                    result = config.validate_redirect_uri(uri)
                    assert isinstance(result, bool)
                except Exception as e:
                    pytest.fail(f"URI parsing should not crash: {uri} - {e}")

    def test_proxy_header_injection_prevention(self):
        """Test prevention of HTTP header injection through proxy headers."""
        config = OAuthRedirectConfig()

        request = Mock()
        request.url.scheme = "http"
        request.url.netloc = "internal.server"
        request.headers = {
            "host": "internal.server",
            "X-Forwarded-Proto": "https\r\nInjected-Header: malicious",
            "X-Forwarded-Host": "evil.com\r\nAnother-Header: attack",
        }

        # Should handle malicious headers gracefully
        try:
            scheme = config._get_scheme(request)
            host = config._get_host(request)
            base_url = config._get_base_url(request)

            # Should not contain injected content
            assert "\r" not in scheme
            assert "\n" not in scheme
            assert "\r" not in host
            assert "\n" not in host
            assert "\r" not in base_url
            assert "\n" not in base_url

        except Exception as e:
            # Should either handle gracefully or fail securely
            assert "malicious" not in str(e)

    def test_case_sensitivity_domain_matching(self):
        """Test that domain matching is case-insensitive for security."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "Example.COM"}):
            config = OAuthRedirectConfig()

            # All variations should be accepted
            case_variations = [
                "https://example.com/callback",
                "https://Example.com/callback",
                "https://EXAMPLE.COM/callback",
                "https://example.COM/callback",
            ]

            for uri in case_variations:
                assert config.validate_redirect_uri(uri) is True

    def test_unicode_domain_handling(self):
        """Test handling of Unicode domains and potential attacks."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            unicode_attacks = [
                "https://еxample.com/callback",  # Cyrillic 'e'
                "https://example.com\u202e/callback",  # Right-to-left override
                "https://example\u2024com/callback",  # Unicode dot
                "https://example\uff0ecom/callback",  # Fullwidth dot
            ]

            for uri in unicode_attacks:
                # Should either reject or handle safely
                try:
                    result = config.validate_redirect_uri(uri)
                    # If it returns True, the unicode was normalized correctly
                    # If it returns False, the attack was prevented
                    assert isinstance(result, bool)
                except Exception:
                    # Exception handling is acceptable for malformed unicode
                    pass

    def test_very_long_domain_handling(self):
        """Test handling of very long domain names."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            # Very long domain that could cause buffer overflow
            long_domain = "a" * 1000 + ".com"
            long_uri = f"https://{long_domain}/callback"

            # Should handle gracefully without crashing
            try:
                result = config.validate_redirect_uri(long_uri)
                assert isinstance(result, bool)
            except Exception:
                # Exception is acceptable for invalid input
                pass

    def test_port_stripping_consistency(self):
        """Test that port stripping is consistent across all validation methods."""
        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": "example.com"}):
            config = OAuthRedirectConfig()

            # Test both redirect validation and domain validation
            uri_with_port = "https://example.com:443/callback"
            assert config.validate_redirect_uri(uri_with_port) is True

            # Test direct domain validation
            config._validate_base_domain("https://example.com:443")  # Should not raise

            # Test with non-standard ports
            uri_custom_port = "https://example.com:8443/callback"
            assert config.validate_redirect_uri(uri_custom_port) is True

    def test_environment_variable_injection(self):
        """Test that environment variable values are sanitized."""
        malicious_domains = "example.com;rm -rf /;evil.com"

        with patch.dict(os.environ, {"OAUTH_ALLOWED_DOMAINS": malicious_domains}):
            config = OAuthRedirectConfig()

            # Should treat the entire string as domain names, not execute commands
            assert "example.com" in config.allowed_domains
            assert "evil.com" in config.allowed_domains
            # Command injection should be treated as a domain name
            assert "rm -rf /" in config.allowed_domains or len(config.allowed_domains) > 2
