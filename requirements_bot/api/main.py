from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from requirements_bot.api.middleware import ExceptionHandlingMiddleware
from requirements_bot.api.routes import questions, sessions

app = FastAPI(
    title="Requirements Bot API",
    description="HTTP API for the Requirements Bot - AI-powered requirements gathering tool",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Restrict to specific origins
    allow_credentials=False,  # Disable until authentication is implemented
    allow_methods=["GET", "POST", "DELETE"],  # Only allow necessary methods
    allow_headers=["Content-Type"],  # Restrict headers
)

# Add unified exception handling middleware
app.add_middleware(ExceptionHandlingMiddleware)

app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(questions.router, prefix="/api/v1", tags=["questions"])


@app.get("/")
async def root():
    return {"message": "Requirements Bot API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
