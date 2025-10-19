"""Error handling helpers for API routes."""

from typing import NoReturn

from fastapi import HTTPException
from pydantic import ValidationError

from specscribe.core.logging import log_event
from specscribe.providers.exceptions import OverloadedError


def handle_overloaded_error(e: OverloadedError, session_id: str, user_id: str) -> NoReturn:
    """Handle AI service overload errors."""
    log_event("retry_requirements.overloaded_error", session_id=session_id, user_id=user_id, error=str(e))
    raise HTTPException(
        status_code=503, detail="AI service is currently overloaded. Please try again in a few moments."
    )


def handle_validation_error(e: ValidationError, session_id: str, user_id: str) -> NoReturn:
    """Handle requirements validation errors."""
    log_event("retry_requirements.validation_error", session_id=session_id, user_id=user_id, error=str(e))
    raise HTTPException(
        status_code=500,
        detail="Requirements generation failed due to validation error. Please contact support.",
    )


def handle_data_error(e: Exception, session_id: str, user_id: str) -> NoReturn:
    """Handle data-related errors (KeyError, TypeError, ValueError)."""
    log_event(
        "retry_requirements.data_error",
        session_id=session_id,
        user_id=user_id,
        error_type=type(e).__name__,
        error=str(e),
    )
    raise HTTPException(status_code=500, detail="An error occurred processing session data. Please contact support.")


def handle_unexpected_error(e: Exception, session_id: str, user_id: str) -> NoReturn:
    """Handle truly unexpected errors."""
    log_event(
        "retry_requirements.unexpected_error",
        session_id=session_id,
        user_id=user_id,
        error_type=type(e).__name__,
        error=str(e),
    )
    raise HTTPException(status_code=500, detail="An unexpected error occurred during retry. Please try again later.")
