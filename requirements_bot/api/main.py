import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from requirements_bot.api.auth import get_jwt_service
from requirements_bot.api.exceptions import SessionNotFoundAPIException, ValidationException
from requirements_bot.api.middleware import AuthenticationMiddleware, ExceptionHandlingMiddleware
from requirements_bot.api.routes import auth, questions, sessions

app = FastAPI(
    title="Requirements Bot API",
    description="HTTP API for the Requirements Bot - AI-powered requirements gathering tool",
    version="0.1.0",
)

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

# Add authentication middleware (before exception handling)
app.add_middleware(AuthenticationMiddleware, jwt_service=get_jwt_service())

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
    return JSONResponse(
        status_code=422,
        content={"error": "ValidationError", "message": "Request validation failed", "details": str(exc)},
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
