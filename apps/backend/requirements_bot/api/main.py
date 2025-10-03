import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from requirements_bot.api.dependencies import get_jwt_service_with_refresh
from requirements_bot.api.error_responses import ErrorDetail
from requirements_bot.api.exceptions import SessionNotFoundAPIException, ValidationException
from requirements_bot.api.middleware import (
    AuthenticationMiddleware,
    ExceptionHandlingMiddleware,
    RequestIDMiddleware,
)
from requirements_bot.api.routes import auth, questions, sessions
from requirements_bot.core.logging import init_logging

app = FastAPI(
    title="Requirements Bot API",
    description="HTTP API for the Requirements Bot - AI-powered requirements gathering tool",
    version="0.1.0",
)

# Initialize structured logging for the API server
init_logging(
    level=os.getenv("REQBOT_LOG_LEVEL", "INFO"),
    fmt=os.getenv("REQBOT_LOG_FORMAT", "json"),
    file_path=os.getenv("REQBOT_LOG_FILE"),
    mask=os.getenv("REQBOT_LOG_MASK", "false").lower() in ("true", "1", "yes", "on"),
    use_stderr=True,  # Use stderr for better separation from app output
)

# Add session middleware for OAuth state management
session_secret = os.getenv("JWT_SECRET_KEY")
if not session_secret:
    raise ValueError("JWT_SECRET_KEY environment variable is required for session middleware")
app.add_middleware(SessionMiddleware, secret_key=session_secret)

# Configure CORS for production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Configurable origins for production
    allow_credentials=True,  # Enable for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Standard REST methods
    allow_headers=["Content-Type", "Authorization"],  # Required headers for auth
    max_age=86400,  # Cache preflight requests for 24 hours
)

# Add request ID middleware (first, so all logs have request ID)
app.add_middleware(RequestIDMiddleware)

# Add authentication middleware (before exception handling)
app.add_middleware(AuthenticationMiddleware, jwt_service=get_jwt_service_with_refresh())

# Add unified exception handling middleware
app.add_middleware(ExceptionHandlingMiddleware)

app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(questions.router, prefix="/api/v1", tags=["questions"])


# Exception handler for validation exceptions from dependency injection
@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=exc.status_code, content={"error": "ValidationError", "message": exc.detail, "details": None}
    )


# Exception handler for Pydantic request validation errors
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        details.append(ErrorDetail(type="validation", message=error["msg"], field=field))

    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_failed",
            "message": "Request validation failed",
            "details": [detail.dict() for detail in details],
            "status_code": 422,
        },
    )


# Exception handler for session not found errors
@app.exception_handler(SessionNotFoundAPIException)
async def session_not_found_exception_handler(request: Request, exc: SessionNotFoundAPIException):
    return JSONResponse(
        status_code=exc.status_code, content={"error": "SessionNotFound", "message": exc.detail, "details": None}
    )


@app.get("/")
async def root():
    return {"message": "Requirements Bot API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
