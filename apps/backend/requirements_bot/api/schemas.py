from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.models import Answer, Question, Requirement


class SessionCreateRequest(BaseModel):
    project: str = Field(
        ..., min_length=1, max_length=200, description="Project name for the requirements gathering session"
    )

    @field_validator("project")
    @classmethod
    def validate_project_name(cls, v):
        # First trim whitespace including tabs
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Project name cannot be empty or only whitespace")
        # Check for forbidden characters in the trimmed value (prevent XSS/injection)
        forbidden_chars = ["<", ">", '"', "'", "&", "\n", "\r", "\t"]
        if any(char in trimmed for char in forbidden_chars):
            raise ValueError("Project name contains invalid characters")
        return trimmed


class SessionCreateResponse(BaseModel):
    id: str
    project: str
    conversation_state: ConversationState
    created_at: datetime


class SessionListResponse(BaseModel):
    sessions: list["SessionSummary"]


class SessionSummary(BaseModel):
    id: str
    project: str
    conversation_state: ConversationState
    conversation_complete: bool
    questions_count: int
    answers_count: int
    requirements_count: int
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(BaseModel):
    id: str
    project: str
    questions: list[Question]
    answers: list[Answer]
    requirements: list[Requirement]
    conversation_complete: bool
    conversation_state: ConversationState
    created_at: datetime
    updated_at: datetime


class SessionContinueResponse(BaseModel):
    session_id: str
    next_question: Question | None
    conversation_complete: bool
    conversation_state: ConversationState


class QuestionAnswerRequest(BaseModel):
    answer_text: str = Field(..., min_length=1, max_length=5000, description="Answer text for the current question")

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, v):
        # First trim whitespace
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Answer cannot be empty or only whitespace")
        # Check for excessively long answers that might indicate spam
        if len(trimmed) > 5000:
            raise ValueError("Answer exceeds maximum length of 5000 characters")
        return trimmed


class AnswerSubmissionResponse(BaseModel):
    session_id: str
    question: Question
    answer: Answer
    conversation_complete: bool
    conversation_state: ConversationState
    requirements_generated: bool = False


class QuestionAnswerResponse(BaseModel):
    session_id: str
    question: Question
    answer: Answer
    next_question: Question | None
    conversation_complete: bool
    conversation_state: ConversationState
    requirements_generated: bool = False


class SessionStatusResponse(BaseModel):
    session_id: str
    conversation_state: ConversationState
    conversation_complete: bool
    current_question: Question | None
    progress: "SessionProgress"


class SessionProgress(BaseModel):
    total_questions: int
    answered_questions: int
    remaining_questions: int
    completion_percentage: float


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: str | None = None


class RetryRequirementsResponse(BaseModel):
    """Response from retry requirements generation endpoint."""

    message: str
    session_id: str
    requirements_count: int
    conversation_state: ConversationState
