"""Middleware for exception handling and other cross-cutting concerns."""

import logging
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
from requirements_bot.core.storage import (
    SessionDeleteError,
    SessionLoadError,
    SessionNotFoundError,
    SessionSaveError,
    StorageError,
)

logger = logging.getLogger(__name__)


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

    def __init__(self, app, jwt_service):
        super().__init__(app)
        self.jwt_service = jwt_service
        # Public routes that don't require authentication
        self.public_routes = {
            "/api/v1/auth/login",
            "/api/v1/auth/callback",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/health",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check authentication for protected routes."""
        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Skip authentication for preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            # Extract and validate token
            token = self._extract_token(request)
            user_info = self.jwt_service.verify_token(token)

            # Add user info to request state
            request.state.user_id = user_info["user_id"]
            request.state.user_email = user_info["email"]

            return await call_next(request)

        except Exception as exc:
            return self._create_auth_error_response(str(exc))

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public and doesn't require authentication."""
        return any(path.startswith(route) for route in self.public_routes)

    def _extract_token(self, request: Request) -> str:
        """Extract JWT token from Authorization header."""
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise Exception("Missing Authorization header")

        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise Exception("Invalid authentication scheme")
            return token
        except ValueError:
            raise Exception("Invalid Authorization header format")

    def _create_auth_error_response(self, message: str) -> JSONResponse:
        """Create authentication error response."""
        content = {"error": "AuthenticationError", "message": message, "details": None}
        return JSONResponse(status_code=HTTP_401_UNAUTHORIZED, content=content, headers={"WWW-Authenticate": "Bearer"})
