"""Decorators for API route handlers."""

from collections.abc import Callable
from functools import wraps

from specscribe.api.exceptions import (
    AnswerNotFoundException,
    QuestionNotFoundException,
    SessionInvalidStateException,
)
from specscribe.core.services import AnswerNotFoundError, QuestionNotFoundError, SessionCompleteError


def handle_service_errors(func: Callable) -> Callable:
    """Decorator to handle service layer exceptions and convert to API exceptions.

    Handles:
    - QuestionNotFoundError -> QuestionNotFoundException
    - AnswerNotFoundError -> AnswerNotFoundException
    - SessionCompleteError -> SessionInvalidStateException
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except QuestionNotFoundError as e:
            raise QuestionNotFoundException(e.question_id) from e
        except AnswerNotFoundError as e:
            raise AnswerNotFoundException(e.question_id) from e
        except SessionCompleteError as e:
            raise SessionInvalidStateException(str(e)) from e

    return wrapper
