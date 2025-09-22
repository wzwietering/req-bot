import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed, reset_time)."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] < window_start:
            request_times.popleft()

        # Check if under limit
        if len(request_times) < self.max_requests:
            request_times.append(now)
            return True, int(window_start + self.window_seconds)
        else:
            # Return when the oldest request will expire
            return False, int(request_times[0] + self.window_seconds)

    def cleanup_expired(self):
        """Clean up expired entries."""
        now = time.time()
        window_start = now - self.window_seconds

        for identifier in list(self.requests.keys()):
            request_times = self.requests[identifier]
            while request_times and request_times[0] < window_start:
                request_times.popleft()

            if not request_times:
                del self.requests[identifier]


class RateLimitMiddleware:
    """Rate limiting middleware for specific endpoints."""

    def __init__(self, oauth_rate_limiter: RateLimiter):
        self.oauth_rate_limiter = oauth_rate_limiter

    def get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if available (for proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host

        return client_ip

    def check_oauth_rate_limit(self, request: Request):
        """Check rate limit for OAuth endpoints."""
        # Only apply to OAuth endpoints
        path = str(request.url.path)
        if not (path.startswith("/api/v1/auth/login/") or path.startswith("/api/v1/auth/callback/")):
            return

        identifier = self.get_client_identifier(request)
        allowed, reset_time = self.oauth_rate_limiter.is_allowed(identifier)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many OAuth requests. Please try again later.",
                    "details": [{"type": "rate_limit", "message": f"Rate limit reset at {reset_time}"}],
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                },
                headers={"Retry-After": str(reset_time - int(time.time()))},
            )


# Global rate limiters
oauth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)  # 5 OAuth attempts per minute
rate_limit_middleware = RateLimitMiddleware(oauth_rate_limiter)
