from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from specscribe.core.storage import (
    SessionDeleteError,
    SessionLoadError,
    SessionNotFoundError,
    SessionSaveError,
    StorageError,
)


class APIException(HTTPException):
    """Base API exception class."""

    pass


class SessionNotFoundAPIException(APIException):
    def __init__(self, session_id: str):
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")


class SessionInvalidStateException(APIException):
    def __init__(self, message: str):
        super().__init__(status_code=HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


class ValidationException(APIException):
    def __init__(self, message: str):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, detail=message)


class InvalidSessionIdException(ValidationException):
    def __init__(self, session_id: str):
        super().__init__(f"Invalid session ID format: {session_id}")


class QuestionNotFoundException(APIException):
    def __init__(self, question_id: str):
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail=f"Question {question_id} not found")


class AnswerNotFoundException(APIException):
    def __init__(self, answer_id: str):
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail=f"Answer {answer_id} not found")


class QuestionAlreadyAnsweredException(APIException):
    def __init__(self, question_id: str):
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Question {question_id} has already been answered. Delete the answer first.",
        )


async def storage_exception_handler(request: Request, exc: StorageError) -> JSONResponse:
    """Handle storage-related exceptions."""
    if isinstance(exc, SessionNotFoundError):
        return JSONResponse(
            status_code=HTTP_404_NOT_FOUND, content={"error": "SessionNotFound", "message": str(exc), "details": None}
        )
    elif isinstance(exc, (SessionSaveError, SessionLoadError, SessionDeleteError)):
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "StorageError", "message": "Database operation failed", "details": str(exc)},
        )
    else:
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "StorageError", "message": "Unexpected storage error", "details": str(exc)},
        )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "InternalServerError", "message": "An unexpected error occurred", "details": str(exc)},
    )
