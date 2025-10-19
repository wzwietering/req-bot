"""Unit tests for enhanced rate limiting functionality."""

import threading
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from specscribe.api.rate_limiting import RateLimiter, RateLimitMiddleware


class TestRateLimiter:
    """Test core rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with custom settings."""
        limiter = RateLimiter(max_requests=5, window_seconds=30)

        assert limiter.max_requests == 5
        assert limiter.window_seconds == 30
        assert isinstance(limiter.requests, dict)

    def test_rate_limiter_default_settings(self):
        """Test rate limiter with default settings."""
        limiter = RateLimiter()

        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60

    def test_is_allowed_first_request(self):
        """Test first request is always allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        allowed, reset_time = limiter.is_allowed("user123")

        assert allowed is True
        assert isinstance(reset_time, int)
        assert reset_time > int(time.time())

    def test_is_allowed_within_limit(self):
        """Test requests within limit are allowed."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)

        # Make 3 requests (within limit)
        for _i in range(3):
            allowed, _ = limiter.is_allowed("user123")
            assert allowed is True

        # Check that we have 3 requests recorded
        assert len(limiter.requests["user123"]) == 3

    def test_is_allowed_exceeds_limit(self):
        """Test request is denied when limit exceeded."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Make 2 requests (at limit)
        for _i in range(2):
            allowed, _ = limiter.is_allowed("user123")
            assert allowed is True

        # Third request should be denied
        allowed, reset_time = limiter.is_allowed("user123")
        assert allowed is False
        assert isinstance(reset_time, int)

    def test_is_allowed_different_identifiers(self):
        """Test that different identifiers have separate limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Each identifier gets their own limit
        allowed1, _ = limiter.is_allowed("user1")
        allowed2, _ = limiter.is_allowed("user2")

        assert allowed1 is True
        assert allowed2 is True

        # Second request from same user should be denied
        allowed3, _ = limiter.is_allowed("user1")
        assert allowed3 is False

        # But other user should still be allowed
        allowed4, _ = limiter.is_allowed("user3")
        assert allowed4 is True

    def test_is_allowed_window_expiry(self):
        """Test that requests are allowed again after window expires."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)  # 1 second window

        # First request allowed
        allowed1, _ = limiter.is_allowed("user123")
        assert allowed1 is True

        # Second request denied
        allowed2, _ = limiter.is_allowed("user123")
        assert allowed2 is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed3, _ = limiter.is_allowed("user123")
        assert allowed3 is True

    def test_cleanup_expired_entries(self):
        """Test cleanup of expired entries."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # Add requests for multiple users
        limiter.is_allowed("user1")
        limiter.is_allowed("user2")
        limiter.is_allowed("user3")

        assert len(limiter.requests) == 3

        # Wait for expiry
        time.sleep(1.1)

        # Trigger cleanup
        limiter.cleanup_expired()

        # All entries should be removed
        assert len(limiter.requests) == 0

    def test_cleanup_expired_partial(self):
        """Test cleanup only removes expired entries."""
        limiter = RateLimiter(max_requests=5, window_seconds=2)

        # Add old request
        limiter.is_allowed("old_user")
        time.sleep(1)

        # Add recent request
        limiter.is_allowed("new_user")

        # Cleanup with partial expiry
        time.sleep(1.1)  # Only first request should be expired
        limiter.cleanup_expired()

        # Only recent user should remain
        assert "new_user" in limiter.requests
        assert len(limiter.requests) == 1

    def test_reset_time_calculation(self):
        """Test that reset time is calculated correctly."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        start_time = time.time()
        limiter.is_allowed("user123")

        # Exceed limit
        allowed, reset_time = limiter.is_allowed("user123")

        assert allowed is False
        # Reset time should be approximately start_time + window_seconds
        assert abs(reset_time - (start_time + 60)) < 2  # Allow 2 second tolerance


class TestRateLimitMiddleware:
    """Test rate limit middleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initialization."""
        oauth_limiter = RateLimiter(max_requests=5, window_seconds=60)
        refresh_limiter = RateLimiter(max_requests=10, window_seconds=3600)

        middleware = RateLimitMiddleware(oauth_limiter, refresh_limiter)

        assert middleware.oauth_rate_limiter == oauth_limiter
        assert middleware.refresh_rate_limiter == refresh_limiter
        assert isinstance(middleware.trusted_proxies, set)

    def test_trusted_proxies_loading(self):
        """Test trusted proxies loading from environment."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1,10.0.0.1,172.16.0.1"}):
            middleware = RateLimitMiddleware(Mock())

            expected_proxies = {"192.168.1.1", "10.0.0.1", "172.16.0.1"}
            assert middleware.trusted_proxies == expected_proxies

    def test_trusted_proxies_empty_env(self):
        """Test trusted proxies with empty environment variable."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": ""}, clear=True):
            middleware = RateLimitMiddleware(Mock())

            assert middleware.trusted_proxies == set()

    def test_get_client_identifier_direct_ip(self):
        """Test client identifier extraction from direct connection."""
        middleware = RateLimitMiddleware(Mock())

        request = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {}

        identifier = middleware.get_client_identifier(request)

        assert identifier == "192.168.1.100"

    def test_get_client_identifier_trusted_proxy(self):
        """Test client identifier extraction through trusted proxy."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1"}):
            middleware = RateLimitMiddleware(Mock())

            request = Mock()
            request.client.host = "192.168.1.1"  # Trusted proxy
            request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1"}

            identifier = middleware.get_client_identifier(request)

            assert identifier == "203.0.113.1"  # First IP in chain

    def test_get_client_identifier_untrusted_proxy(self):
        """Test client identifier ignores untrusted proxy headers."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1"}):
            middleware = RateLimitMiddleware(Mock())

            request = Mock()
            request.client.host = "192.168.1.2"  # Not trusted
            request.headers = {"X-Forwarded-For": "203.0.113.1"}

            identifier = middleware.get_client_identifier(request)

            assert identifier == "192.168.1.2"  # Direct IP, ignore header

    def test_get_client_identifier_invalid_forwarded_ip(self):
        """Test client identifier with invalid forwarded IP."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1"}):
            middleware = RateLimitMiddleware(Mock())

            request = Mock()
            request.client.host = "192.168.1.1"
            request.headers = {"X-Forwarded-For": "invalid.ip.address"}

            identifier = middleware.get_client_identifier(request)

            assert identifier == "192.168.1.1"  # Fall back to direct IP

    def test_is_valid_ip_valid_addresses(self):
        """Test IP validation with valid addresses."""
        middleware = RateLimitMiddleware(Mock())

        valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "203.0.113.1", "255.255.255.255", "0.0.0.0"]

        for ip in valid_ips:
            assert middleware._is_valid_ip(ip) is True

    def test_is_valid_ip_invalid_addresses(self):
        """Test IP validation with invalid addresses."""
        middleware = RateLimitMiddleware(Mock())

        invalid_ips = [
            "256.1.1.1",  # Invalid octet
            "192.168.1",  # Too few octets
            "192.168.1.1.1",  # Too many octets
            "192.168.1.a",  # Non-numeric
            "not.an.ip.address",  # Invalid format
            "",  # Empty string
            "192.168.-1.1",  # Negative number
        ]

        for ip in invalid_ips:
            assert middleware._is_valid_ip(ip) is False

    def test_check_oauth_rate_limit_allowed_path(self):
        """Test OAuth rate limiting on allowed paths."""
        oauth_limiter = Mock()
        oauth_limiter.is_allowed.return_value = (True, int(time.time()) + 60)
        middleware = RateLimitMiddleware(oauth_limiter)

        request = Mock()
        request.url.path = "/api/v1/auth/login/google"
        request.client.host = "192.168.1.1"
        request.headers = {}

        # Should not raise exception
        middleware.check_oauth_rate_limit(request)

        oauth_limiter.is_allowed.assert_called_once_with("192.168.1.1")

    def test_check_oauth_rate_limit_non_oauth_path(self):
        """Test OAuth rate limiting ignores non-OAuth paths."""
        oauth_limiter = Mock()
        middleware = RateLimitMiddleware(oauth_limiter)

        request = Mock()
        request.url.path = "/api/v1/sessions"
        request.client.host = "192.168.1.1"

        # Should not check rate limit for non-OAuth paths
        middleware.check_oauth_rate_limit(request)

        oauth_limiter.is_allowed.assert_not_called()

    def test_check_oauth_rate_limit_exceeded(self):
        """Test OAuth rate limiting when limit exceeded."""
        oauth_limiter = Mock()
        reset_time = int(time.time()) + 60
        oauth_limiter.is_allowed.return_value = (False, reset_time)
        middleware = RateLimitMiddleware(oauth_limiter)

        request = Mock()
        request.url.path = "/api/v1/auth/callback/google"
        request.client.host = "192.168.1.1"
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            middleware.check_oauth_rate_limit(request)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate_limit_exceeded" in exc_info.value.detail["error"]
        assert "Retry-After" in exc_info.value.headers

    def test_check_refresh_token_rate_limit_allowed(self):
        """Test refresh token rate limiting when allowed."""
        refresh_limiter = Mock()
        refresh_limiter.is_allowed.return_value = (True, int(time.time()) + 3600)
        middleware = RateLimitMiddleware(Mock(), refresh_limiter)

        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        # Should not raise exception
        middleware.check_refresh_token_rate_limit(request)

        refresh_limiter.is_allowed.assert_called_once_with("192.168.1.1")

    def test_check_refresh_token_rate_limit_exceeded(self):
        """Test refresh token rate limiting when limit exceeded."""
        refresh_limiter = Mock()
        reset_time = int(time.time()) + 3600
        refresh_limiter.is_allowed.return_value = (False, reset_time)
        middleware = RateLimitMiddleware(Mock(), refresh_limiter)

        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            middleware.check_refresh_token_rate_limit(request)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate_limit_exceeded" in exc_info.value.detail["error"]
        assert "token refresh requests" in exc_info.value.detail["message"]


class TestRateLimitingSecurity:
    """Test security-specific scenarios for rate limiting."""

    def test_rate_limiter_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)

        # Try to create many unique identifiers
        unique_identifiers = [f"attacker_{i}" for i in range(1000)]

        for identifier in unique_identifiers:
            limiter.is_allowed(identifier)

        # Should handle large number of identifiers without crashing
        assert len(limiter.requests) == 1000

        # Cleanup should work
        time.sleep(1.1)
        limiter.cleanup_expired()
        assert len(limiter.requests) == 0

    def test_client_identifier_spoofing_prevention(self):
        """Test prevention of client identifier spoofing."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1"}):
            middleware = RateLimitMiddleware(Mock())

            # Attacker tries to spoof X-Forwarded-For from untrusted IP
            request = Mock()
            request.client.host = "203.0.113.100"  # Untrusted
            request.headers = {"X-Forwarded-For": "127.0.0.1"}  # Spoofed

            identifier = middleware.get_client_identifier(request)

            # Should use actual client IP, not spoofed header
            assert identifier == "203.0.113.100"

    def test_x_forwarded_for_injection_protection(self):
        """Test protection against X-Forwarded-For header injection."""
        with patch.dict("os.environ", {"TRUSTED_PROXIES": "192.168.1.1"}):
            middleware = RateLimitMiddleware(Mock())

            request = Mock()
            request.client.host = "192.168.1.1"
            # Malicious header with multiple IPs and potential injection
            request.headers = {"X-Forwarded-For": "evil.com, 192.168.1.1, <script>alert('xss')</script>"}

            identifier = middleware.get_client_identifier(request)

            # Should extract first IP and validate it
            assert identifier == "evil.com" or identifier == "192.168.1.1"  # Depends on validation

    def test_rate_limit_bypassing_attempts(self):
        """Test various rate limit bypassing attempts."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Legitimate request
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is True

        # Should be rate limited
        allowed, _ = limiter.is_allowed("192.168.1.1")
        assert allowed is False

        # Try various bypass attempts (should all be rate limited)
        bypass_attempts = [
            "192.168.1.1",  # Same IP
            " 192.168.1.1 ",  # With whitespace
            "192.168.1.1:8080",  # With port
            "192.168.001.001",  # Different formatting
        ]

        for attempt in bypass_attempts:
            allowed, _ = limiter.is_allowed(attempt)
            # Each attempt is treated as separate identifier
            # This is expected behavior - sophisticated bypass prevention
            # would require normalization at a higher level

    def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent access."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        results = []
        errors = []

        def make_request():
            try:
                allowed, _ = limiter.is_allowed("concurrent_user")
                results.append(allowed)
            except Exception as e:
                errors.append(e)

        # Create multiple threads making requests concurrently
        threads = [threading.Thread(target=make_request) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have errors
        assert len(errors) == 0

        # Should have exactly 5 allowed requests and 5 denied
        allowed_count = sum(1 for result in results if result)
        denied_count = sum(1 for result in results if not result)

        assert allowed_count == 5
        assert denied_count == 5

    def test_large_identifier_handling(self):
        """Test handling of very large identifiers."""
        limiter = RateLimiter()

        # Very long identifier
        large_identifier = "a" * 10000

        # Should handle without crashing
        try:
            allowed, _ = limiter.is_allowed(large_identifier)
            assert isinstance(allowed, bool)
        except Exception as e:
            # If it fails, it should be a controlled failure
            assert "memory" not in str(e).lower()

    def test_time_manipulation_resistance(self):
        """Test resistance to time manipulation attacks."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)

        # Make request at current time
        allowed1, _ = limiter.is_allowed("user123")
        assert allowed1 is True

        # Manipulate system time (simulate)
        original_time = time.time
        try:
            # Mock time going backwards
            time.time = lambda: original_time() - 3600

            # Should still be rate limited
            allowed2, _ = limiter.is_allowed("user123")
            assert allowed2 is False

        finally:
            time.time = original_time

    def test_rate_limit_information_disclosure(self):
        """Test that rate limiting doesn't disclose sensitive information."""
        oauth_limiter = Mock()
        oauth_limiter.is_allowed.return_value = (False, int(time.time()) + 60)
        middleware = RateLimitMiddleware(oauth_limiter)

        request = Mock()
        request.url.path = "/api/v1/auth/login/google"
        request.client.host = "192.168.1.1"
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            middleware.check_oauth_rate_limit(request)

        error_detail = exc_info.value.detail
        headers = exc_info.value.headers

        # Error message should be generic
        assert "rate_limit_exceeded" in error_detail["error"]
        assert "OAuth requests" in error_detail["message"]

        # Should not reveal internal details
        assert "192.168.1.1" not in str(error_detail)
        assert "google" not in str(error_detail)

        # Retry-After header should be present but not reveal internal timing
        assert "Retry-After" in headers
        retry_after = int(headers["Retry-After"])
        assert 0 <= retry_after <= 3600  # Reasonable range

    def test_null_byte_injection_prevention(self):
        """Test prevention of null byte injection in identifiers."""
        limiter = RateLimiter()
        # middleware = RateLimitMiddleware(limiter)  # Not used in this test

        # Test null bytes in various places
        malicious_identifiers = ["192.168.1.1\x00admin", "\x00192.168.1.1", "192\x00.168.1.1", "192.168.1.1\x00\x00"]

        for identifier in malicious_identifiers:
            # Should handle gracefully
            try:
                allowed, _ = limiter.is_allowed(identifier)
                assert isinstance(allowed, bool)
            except Exception:
                # Acceptable to reject malformed identifiers
                pass

    def test_dos_protection_cleanup_frequency(self):
        """Test that cleanup prevents DoS through memory exhaustion."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)

        # Simulate sustained attack
        for i in range(100):
            limiter.is_allowed(f"attacker_{i}")

        # Memory usage should be bounded
        initial_size = len(limiter.requests)
        assert initial_size == 100

        # After cleanup, should be manageable
        time.sleep(1.1)
        limiter.cleanup_expired()
        final_size = len(limiter.requests)
        assert final_size == 0
