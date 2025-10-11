import json
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import ValidationError

from requirements_bot.core.logging import log_event
from requirements_bot.core.models import (
    AnswerAnalysis,
    CompletenessAssessment,
    Question,
    Requirement,
)

T = TypeVar("T")


class ProviderError(Exception):
    """Base exception for provider operations."""

    pass


class ProviderConnectionError(ProviderError):
    """Raised when provider connection fails."""

    pass


class ProviderResponseError(ProviderError):
    """Raised when provider returns invalid response."""

    pass


class ProviderParseError(ProviderError):
    """Raised when response cannot be parsed."""

    pass


class OverloadedError(ProviderError):
    """Raised when provider is overloaded (429/529 errors)."""

    pass


def retry_with_exponential_backoff(
    operation_func: Callable[[], T],
    max_retries: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
) -> T:
    """
    Retry operation with exponential backoff.

    Args:
        operation_func: Function to execute that may raise OverloadedError
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Result from operation_func

    Raises:
        OverloadedError: If all retries exhausted
    """
    for attempt in range(max_retries):
        try:
            return operation_func()
        except OverloadedError:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff with jitter (+/- 10%)
            delay = min(base_delay * (2**attempt), max_delay)
            jitter = delay * random.uniform(-0.1, 0.1)
            actual_delay = max(0, delay + jitter)
            time.sleep(actual_delay)
    raise OverloadedError("Max retries exceeded")


def handle_provider_operation(
    operation: str,
    provider: str,
    model: str,
    operation_func: Callable[[], T],
    fallback_factory: Callable[[], T],
    allow_fallback: bool = True,
) -> T:
    """
    Execute a provider operation with unified exception handling.

    Args:
        operation: The operation being performed (e.g., "generate_questions")
        provider: The provider name (e.g., "openai", "anthropic")
        model: The model being used
        operation_func: Function to execute that may raise exceptions
        fallback_factory: Function that creates fallback response on error
        allow_fallback: Whether to use fallback on critical errors (default True)

    Returns:
        Result from operation_func or fallback response on error

    Raises:
        ValidationError: If Pydantic validation fails and allow_fallback is False
        OverloadedError: If API overloaded and retries exhausted and allow_fallback is False
    """
    try:
        return operation_func()
    except ValidationError as e:
        # Schema mismatch - this is a bug, log details
        log_event(
            "llm.validation_error",
            component="provider",
            operation=operation,
            provider=provider,
            model=model,
            error_type="ValidationError",
            error_msg=str(e),
            error_details=e.errors(),  # Preserve structured validation errors
            level=logging.ERROR,
        )
        if not allow_fallback:
            raise
        # Use fallback but log that we're doing so at ERROR level for critical operations
        critical_operations = ["summarize_requirements", "finalize_session"]
        log_level = logging.ERROR if operation in critical_operations else logging.WARNING
        log_event(
            "llm.using_fallback",
            component="provider",
            operation=operation,
            reason="validation_error",
            level=log_level,
        )
        return fallback_factory()
    except OverloadedError as e:
        # API overloaded - try retry with backoff
        log_event(
            "llm.overloaded_error",
            component="provider",
            operation=operation,
            provider=provider,
            model=model,
            error_type="OverloadedError",
            error_msg=str(e),
        )
        try:
            return retry_with_exponential_backoff(operation_func, max_retries=5)
        except OverloadedError:
            if not allow_fallback:
                raise
            # Log at ERROR level for critical operations
            critical_operations = ["summarize_requirements", "finalize_session"]
            log_level = logging.ERROR if operation in critical_operations else logging.WARNING
            log_event(
                "llm.using_fallback",
                component="provider",
                operation=operation,
                reason="overloaded_retries_exhausted",
                level=log_level,
            )
            return fallback_factory()
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # JSON/data parsing errors
        log_event(
            "llm.parse_error",
            component="provider",
            operation=operation,
            provider=provider,
            model=model,
            error_type=type(e).__name__,
            error_msg=str(e),
        )
        return fallback_factory()
    except Exception as e:
        # All other errors (network, API limits, etc.)
        log_event(
            "llm.provider_error",
            component="provider",
            operation=operation,
            provider=provider,
            model=model,
            error_type=type(e).__name__,
            error_msg=str(e),
        )
        return fallback_factory()


class FallbackFactory:
    """Factory for creating consistent fallback responses."""

    @staticmethod
    def empty_questions_list() -> list[Question]:
        """Fallback for question generation errors."""
        return []

    @staticmethod
    def empty_requirements_list() -> list[Requirement]:
        """Fallback for requirements generation errors."""
        return []

    @staticmethod
    def default_answer_analysis() -> AnswerAnalysis:
        """Fallback for answer analysis errors."""
        return AnswerAnalysis(
            is_complete=True,
            is_specific=True,
            is_consistent=True,
            follow_up_questions=[],
            analysis_notes="Analysis failed - defaulting to accepting answer",
        )

    @staticmethod
    def default_completeness_assessment(num_questions: int) -> CompletenessAssessment:
        """Fallback for completeness assessment errors."""
        return CompletenessAssessment(
            is_complete=num_questions >= 8,
            missing_areas=[],
            confidence_score=0.5,
            reasoning="Assessment failed - using basic heuristics",
        )


def parse_json_response(content: str, error_context: dict[str, Any]) -> Any:
    """
    Parse JSON response with unified error handling.

    Args:
        content: The JSON content to parse
        error_context: Context for error logging

    Returns:
        Parsed JSON data

    Raises:
        ProviderParseError: If parsing fails
    """
    if not content:
        raise ProviderParseError("Empty response content")

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        log_event(
            "llm.json_parse_error",
            component="provider",
            operation=error_context.get("operation", "unknown"),
            provider=error_context.get("provider", "unknown"),
            model=error_context.get("model", "unknown"),
            error_msg=str(e),
            content_length=len(content),
        )
        raise ProviderParseError(f"Invalid JSON response: {e}") from e


def extract_content_from_response(response: Any, provider: str) -> str:
    """
    Extract text content from provider-specific response format.

    Args:
        response: The provider response object
        provider: Provider name for format handling

    Returns:
        Extracted text content

    Raises:
        ProviderResponseError: If content extraction fails
    """
    try:
        if provider == "openai":
            return getattr(response, "output_text", "")
        elif provider == "anthropic":
            content = ""
            if hasattr(response, "content") and response.content:
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        content += block.text
            return content
        elif provider == "google":
            return getattr(response, "text", "")
        else:
            raise ProviderResponseError(f"Unknown provider: {provider}")
    except (AttributeError, TypeError) as e:
        raise ProviderResponseError(f"Failed to extract content: {e}") from e
