"""Middleware for exception handling and other cross-cutting concerns."""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
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
        """Handle exception and return consistent JSON response.

        This centralizes all exception handling logic that was previously
        duplicated across route handlers.
        """
        # Log the exception for debugging (but don't expose details to client)
        logger.exception(f"Exception in {request.method} {request.url}: {exc}")

        # Handle core domain exceptions
        if isinstance(exc, SessionNotFoundError):
            return self._create_error_response(
                status_code=HTTP_404_NOT_FOUND, error="SessionNotFound", message=str(exc), details=None
            )

        # Handle storage exceptions
        elif isinstance(exc, (SessionSaveError, SessionLoadError, SessionDeleteError)):
            return self._create_error_response(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error="StorageError",
                message="Database operation failed",
                details=None,  # Don't expose internal error details
            )

        elif isinstance(exc, StorageError):
            return self._create_error_response(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error="StorageError",
                message="Storage operation failed",
                details=None,
            )

        # Handle API-specific exceptions
        elif isinstance(exc, SessionNotFoundAPIException):
            return self._create_error_response(
                status_code=HTTP_404_NOT_FOUND, error="SessionNotFound", message=exc.detail, details=None
            )

        elif isinstance(exc, SessionInvalidStateException):
            return self._create_error_response(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY, error="InvalidSessionState", message=exc.detail, details=None
            )

        elif isinstance(exc, ValidationException):
            return self._create_error_response(
                status_code=HTTP_400_BAD_REQUEST, error="ValidationError", message=exc.detail, details=None
            )

        elif isinstance(exc, APIException):
            return self._create_error_response(
                status_code=exc.status_code, error="APIError", message=exc.detail, details=None
            )

        # Handle validation errors from Pydantic
        elif hasattr(exc, "errors") and callable(exc.errors):
            # This is likely a Pydantic ValidationError
            return self._create_error_response(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                error="ValidationError",
                message="Request validation failed",
                details=str(exc),
            )

        # Handle generic ValueError (but don't treat as "not found")
        elif isinstance(exc, ValueError):
            return self._create_error_response(
                status_code=HTTP_400_BAD_REQUEST,
                error="ValueError",
                message="Invalid request parameters",
                details=None,  # Don't expose internal details
            )

        # Handle all other unexpected exceptions
        else:
            return self._create_error_response(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error="InternalServerError",
                message="An unexpected error occurred",
                details=None,  # Never expose internal error details in production
            )

    def _create_error_response(
        self, status_code: int, error: str, message: str, details: str | None = None
    ) -> JSONResponse:
        """Create a consistent error response format."""
        content = {"error": error, "message": message, "details": details}
        return JSONResponse(status_code=status_code, content=content)
