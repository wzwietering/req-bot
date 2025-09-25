from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Detailed error information."""

    type: str
    message: str
    field: str | None = None


class StandardErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    message: str
    details: list[ErrorDetail] | None = None
    status_code: int


class AuthenticationError(HTTPException):
    """Standardized authentication error."""

    def __init__(self, message: str = "Authentication required", details: list[ErrorDetail] | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": message,
                "details": details or [],
                "status_code": status.HTTP_401_UNAUTHORIZED,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


class ValidationError(HTTPException):
    """Standardized validation error."""

    def __init__(self, message: str, field: str | None = None, details: list[ErrorDetail] | None = None):
        error_details = details or []
        if field and message:
            error_details.append(ErrorDetail(type="validation", message=message, field=field))

        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "validation_failed",
                "message": "Input validation failed",
                "details": [detail.model_dump() for detail in error_details],
                "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            },
        )


class ConfigurationError(HTTPException):
    """Standardized configuration error."""

    def __init__(self, message: str, details: list[ErrorDetail] | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "configuration_error",
                "message": message,
                "details": details or [],
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )


class OAuthError(HTTPException):
    """Standardized OAuth error."""

    def __init__(self, message: str, provider: str | None = None, details: list[ErrorDetail] | None = None):
        error_details = details or []
        if provider:
            error_details.append(ErrorDetail(type="oauth", message=f"Provider: {provider}"))

        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "oauth_error",
                "message": message,
                "details": [detail.model_dump() for detail in error_details],
                "status_code": status.HTTP_400_BAD_REQUEST,
            },
        )


class NotFoundError(HTTPException):
    """Standardized not found error."""

    def __init__(self, resource: str, identifier: str | None = None):
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": message,
                "details": [ErrorDetail(type="not_found", message=f"Resource: {resource}").model_dump()],
                "status_code": status.HTTP_404_NOT_FOUND,
            },
        )


def create_error_response(
    error_type: str, message: str, status_code: int, details: list[ErrorDetail] | None = None
) -> HTTPException:
    """Create a standardized error response."""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_type,
            "message": message,
            "details": [detail.model_dump() for detail in (details or [])],
            "status_code": status_code,
        },
    )
