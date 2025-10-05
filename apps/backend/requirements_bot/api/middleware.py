"""Middleware for exception handling and other cross-cutting concerns."""

import logging
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from requirements_bot.api.exceptions import (
    APIException,
    SessionInvalidStateException,
    SessionNotFoundAPIException,
    ValidationException,
)
from requirements_bot.core.logging import log_event, set_request_id, span
from requirements_bot.core.services.session_cookie_config import SessionCookieConfig
from requirements_bot.core.services.token_config import TokenConfig
from requirements_bot.core.services.user_service import UserService
from requirements_bot.core.storage import (
    SessionDeleteError,
    SessionLoadError,
    SessionNotFoundError,
    SessionSaveError,
    StorageError,
)

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request ID to all logs and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request context and response headers."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state for access by other code
        request.state.request_id = request_id

        # Set in logging context for all subsequent logs
        set_request_id(request_id)

        log_event(
            "request.started",
            level=logging.INFO,
            component="middleware",
            operation="request_id",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        log_event(
            "request.completed",
            level=logging.INFO,
            component="middleware",
            operation="request_id",
            status_code=response.status_code,
        )

        # Clear request ID from context
        set_request_id(None)

        return response


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent exception handling across all endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request and catch exceptions for consistent error responses."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_exception(request, exc)

    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle exception and return consistent JSON response."""
        logger.exception(f"Exception in {request.method} {request.url}: {exc}")

        if self._is_core_domain_exception(exc):
            return self._handle_core_domain_exception(exc)
        elif self._is_storage_exception(exc):
            return self._handle_storage_exception(exc)
        elif self._is_api_exception(exc):
            return self._handle_api_exception(exc)
        elif self._is_validation_exception(exc):
            return self._handle_validation_exception(exc)
        else:
            return self._handle_unknown_exception()

    def _is_core_domain_exception(self, exc: Exception) -> bool:
        """Check if exception is from core domain layer."""
        return isinstance(exc, SessionNotFoundError)

    def _is_storage_exception(self, exc: Exception) -> bool:
        """Check if exception is from storage layer."""
        return isinstance(exc, (SessionSaveError, SessionLoadError, SessionDeleteError, StorageError))

    def _is_api_exception(self, exc: Exception) -> bool:
        """Check if exception is API-specific."""
        return isinstance(
            exc,
            (
                SessionNotFoundAPIException,
                SessionInvalidStateException,
                ValidationException,
                APIException,
            ),
        )

    def _is_validation_exception(self, exc: Exception) -> bool:
        """Check if exception is validation-related."""
        return (hasattr(exc, "errors") and callable(exc.errors)) or isinstance(exc, (ValueError, ValidationException))

    def _handle_core_domain_exception(self, exc: Exception) -> JSONResponse:
        """Handle core domain exceptions."""
        return self._create_error_response(
            status_code=HTTP_404_NOT_FOUND, error="SessionNotFound", message=str(exc), details=None
        )

    def _handle_storage_exception(self, exc: Exception) -> JSONResponse:
        """Handle storage-related exceptions."""
        if isinstance(exc, (SessionSaveError, SessionLoadError, SessionDeleteError)):
            message = "Database operation failed"
        else:
            message = "Storage operation failed"

        return self._create_error_response(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error="StorageError",
            message=message,
            details=None,
        )

    def _handle_api_exception(self, exc: Exception) -> JSONResponse:
        """Handle API-specific exceptions."""
        if isinstance(exc, SessionNotFoundAPIException):
            return self._create_error_response(
                status_code=HTTP_404_NOT_FOUND, error="SessionNotFound", message=exc.detail, details=None
            )
        elif isinstance(exc, SessionInvalidStateException):
            return self._create_error_response(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                error="InvalidSessionState",
                message=exc.detail,
                details=None,
            )
        elif isinstance(exc, ValidationException):
            return self._create_error_response(
                status_code=HTTP_400_BAD_REQUEST, error="ValidationError", message=exc.detail, details=None
            )
        else:  # APIException
            return self._create_error_response(
                status_code=exc.status_code, error="APIError", message=exc.detail, details=None
            )

    def _handle_validation_exception(self, exc: Exception) -> JSONResponse:
        """Handle validation-related exceptions."""
        if hasattr(exc, "errors") and callable(exc.errors):
            return self._create_error_response(
                status_code=HTTP_422_UNPROCESSABLE_CONTENT,
                error="ValidationError",
                message="Request validation failed",
                details=str(exc),
            )
        else:  # ValueError
            return self._create_error_response(
                status_code=HTTP_400_BAD_REQUEST,
                error="ValueError",
                message="Invalid request parameters",
                details=None,
            )

    def _handle_unknown_exception(self) -> JSONResponse:
        """Handle unexpected exceptions."""
        return self._create_error_response(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error="InternalServerError",
            message="An unexpected error occurred",
            details=None,
        )

    def _create_error_response(
        self, status_code: int, error: str, message: str, details: str | None = None
    ) -> JSONResponse:
        """Create a consistent error response format."""
        content = {"error": error, "message": message, "details": details}
        return JSONResponse(status_code=status_code, content=content)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT token authentication."""

    def __init__(self, app, jwt_service, refresh_token_service=None, db_session_factory=None):
        super().__init__(app)
        self.jwt_service = jwt_service
        self.refresh_token_service = refresh_token_service
        self.db_session_factory = db_session_factory
        self.cookie_config = SessionCookieConfig()
        # Public routes that don't require authentication
        self.public_routes = {
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/api/v1/auth/logout",
            "/api/v1/auth/status",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/health",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check authentication for protected routes."""
        log_event(
            "auth.middleware_dispatch",
            level=logging.INFO,
            component="auth",
            operation="dispatch",
            path=request.url.path,
            method=request.method,
            is_public=self._is_public_route(request.url.path),
        )

        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            response = await call_next(request)
            self._add_security_headers(response, request.url.path)
            return response

        # Skip authentication for preflight requests
        if request.method == "OPTIONS":
            response = await call_next(request)
            self._add_security_headers(response, request.url.path)
            return response

        with span(
            "auth.authenticate_request",
            component="auth",
            operation="authenticate",
            path=request.url.path,
            method=request.method,
        ):
            try:
                # Extract and validate token
                token = self._extract_token(request)

                log_event(
                    "auth.token_verification_start",
                    level=logging.INFO,
                    component="auth",
                    operation="verify_token",
                )

                user_info = self.jwt_service.verify_token(token)

                log_event(
                    "auth.authentication_success",
                    component="auth",
                    operation="authenticate",
                    user_id=user_info["user_id"],
                    user_email=user_info.get("email"),
                    path=request.url.path,
                )

                # Add user info to request state
                request.state.user_id = user_info["user_id"]
                request.state.user_email = user_info["email"]

                response = await call_next(request)
                self._add_security_headers(response, request.url.path)
                return response

            except Exception as exc:
                # If token extraction failed, try auto-refresh with refresh token
                if "No authentication token found" in str(exc):
                    refresh_result = self._try_refresh_token(request)
                    if refresh_result:
                        access_token, new_refresh_token, user_email = refresh_result

                        # Verify the new access token and extract user info
                        user_info = self.jwt_service.verify_token(access_token)

                        # Add user info to request state
                        request.state.user_id = user_info["user_id"]
                        request.state.user_email = user_info["email"]

                        # Process the request with the refreshed token
                        response = await call_next(request)

                        # Set new tokens in response cookies
                        self._set_auth_cookies(response, access_token, new_refresh_token)
                        self._add_security_headers(response, request.url.path)
                        return response

                log_event(
                    "auth.authentication_failed",
                    level=logging.WARNING,
                    component="auth",
                    operation="authenticate",
                    error_type=type(exc).__name__,
                    error_msg=str(exc),
                    path=request.url.path,
                )
                return self._create_auth_error_response(str(exc))

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public and doesn't require authentication."""
        # Handle exact match for root path to avoid matching all paths starting with "/"
        if path == "/":
            return True

        # For other routes, check if path starts with any public route prefix
        # Exclude "/" from the check since we handled it above
        return any(path.startswith(route) for route in self.public_routes if route != "/")

    def _extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header or cookie."""
        log_event(
            "auth.token_extraction_start",
            component="auth",
            operation="extract_token",
            path=request.url.path,
            available_cookies=list(request.cookies.keys()),
            has_authorization_header=bool(request.headers.get("Authorization")),
        )

        # Try Authorization header first (for API clients)
        authorization = request.headers.get("Authorization")
        if authorization:
            log_event(
                "auth.trying_authorization_header",
                level=logging.INFO,
                component="auth",
                operation="extract_token",
            )
            try:
                scheme, token = authorization.split(" ", 1)
                if scheme.lower() == "bearer":
                    log_event(
                        "auth.token_extracted_from_header",
                        level=logging.INFO,
                        component="auth",
                        operation="extract_token",
                        token_length=len(token),
                    )
                    return token
                else:
                    log_event(
                        "auth.invalid_authorization_scheme",
                        level=logging.WARNING,
                        component="auth",
                        operation="extract_token",
                        scheme=scheme,
                    )
            except ValueError:
                log_event(
                    "auth.invalid_authorization_header_format",
                    level=logging.WARNING,
                    component="auth",
                    operation="extract_token",
                )

        # Fallback to access_token cookie (for browser clients)
        token = request.cookies.get("access_token")
        if token:
            log_event(
                "auth.token_extracted_from_cookie",
                level=logging.INFO,
                component="auth",
                operation="extract_token",
                token_length=len(token),
            )
            return token

        log_event(
            "auth.no_token_found",
            level=logging.WARNING,
            component="auth",
            operation="extract_token",
            path=request.url.path,
            available_cookies=list(request.cookies.keys()),
        )
        raise Exception("No authentication token found")

    def _try_refresh_token(self, request: Request) -> tuple[str, str, str] | None:
        """Try to refresh access token using refresh token from cookie.

        Returns:
            Tuple of (access_token, new_refresh_token, user_email) if successful, None otherwise
        """
        if not self.refresh_token_service or not self.db_session_factory:
            return None

        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            return None

        log_event(
            "auth.attempting_auto_refresh",
            level=logging.INFO,
            component="auth",
            operation="auto_refresh",
            path=request.url.path,
        )

        with span(
            "auth.auto_refresh_token",
            component="auth",
            operation="auto_refresh",
        ):
            try:
                # Rotate refresh token (revoke old, issue new)
                rotation_result = self.refresh_token_service.refresh_and_rotate(refresh_token)

                if not rotation_result:
                    log_event(
                        "auth.auto_refresh_failed",
                        level=logging.WARNING,
                        component="auth",
                        operation="auto_refresh",
                        reason="Invalid or expired refresh token",
                    )
                    return None

                user_id, new_refresh_token = rotation_result

                # Get user info for new access token
                with self.db_session_factory() as db_session:
                    user_service = UserService(db_session)
                    user = user_service.get_user_by_id(user_id)

                    if not user:
                        log_event(
                            "auth.auto_refresh_failed",
                            level=logging.WARNING,
                            component="auth",
                            operation="auto_refresh",
                            reason="User not found",
                            user_id=user_id,
                        )
                        return None

                    # Create new access token
                    access_token = self.jwt_service.create_access_token(user.id, user.email)

                    log_event(
                        "auth.auto_refresh_success",
                        level=logging.INFO,
                        component="auth",
                        operation="auto_refresh",
                        user_id=user.id,
                    )

                    return (access_token, new_refresh_token, user.email)

            except Exception as exc:
                log_event(
                    "auth.auto_refresh_error",
                    level=logging.ERROR,
                    component="auth",
                    operation="auto_refresh",
                    error_type=type(exc).__name__,
                    error_msg=str(exc),
                )
                return None

    def _set_auth_cookies(self, response: Response, access_token: str, refresh_token: str) -> None:
        """Set authentication cookies on response."""
        token_config = TokenConfig()
        cookie_settings = self.cookie_config.get_cookie_settings()

        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=self.jwt_service.access_token_expire_minutes * 60,
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

        # Set refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=token_config.get_refresh_token_max_age_seconds(),
            httponly=True,
            secure=cookie_settings["secure"],
            samesite=cookie_settings["samesite"],
            path=cookie_settings["path"],
        )

    def _add_security_headers(self, response: Response, path: str) -> None:
        """Add security headers to response.

        Args:
            response: The response to add headers to
            path: The request path (used to determine CSP policy)
        """
        is_docs = path in {"/docs", "/redoc", "/openapi.json"}
        security_headers = self.cookie_config.get_response_headers(for_docs=is_docs)
        for header, value in security_headers.items():
            response.headers[header] = value

    def _create_auth_error_response(self, message: str) -> JSONResponse:
        """Create authentication error response."""
        content = {"error": "AuthenticationError", "message": message, "details": None}
        headers = {"WWW-Authenticate": "Bearer"}
        headers.update(self.cookie_config.get_response_headers())
        return JSONResponse(status_code=HTTP_401_UNAUTHORIZED, content=content, headers=headers)
