from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from requirements_bot.api.validation import validate_non_empty_text
from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.models import Answer, Question, Requirement

# Type alias for question categories
QuestionCategory = Literal["scope", "users", "constraints", "nonfunctional", "interfaces", "data", "risks", "success"]


class SessionCreateRequest(BaseModel):
    project: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Project name for the requirements gathering session",
        examples=["E-commerce Mobile App"],
    )

    @field_validator("project")
    @classmethod
    def validate_project_name(cls, v):
        trimmed = validate_non_empty_text(v, "Project name")
        # Check for forbidden characters (prevent XSS/injection)
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
    answer_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Answer text for the current question",
        examples=["We need a web-based dashboard accessible from desktop and mobile devices"],
    )

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, v):
        return validate_non_empty_text(v, "Answer", max_length=5000)


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


class QuestionAnswerPair(BaseModel):
    """A question paired with its answer (if answered)."""

    question: Question
    answer: Answer | None


class SessionQAResponse(BaseModel):
    """Response containing all questions and answers for a session."""

    session_id: str
    project: str
    qa_pairs: list[QuestionAnswerPair]


# Question CRUD schemas
class QuestionCreateRequest(BaseModel):
    """Request to create a new question."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question text",
        examples=["What is the expected timeline for this project?"],
    )
    category: QuestionCategory = Field(..., examples=["constraints"])
    required: bool = Field(True, examples=[True])

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return validate_non_empty_text(v, "Question text")


class QuestionUpdateRequest(BaseModel):
    """Request to update a question."""

    text: str | None = Field(
        None, min_length=1, max_length=1000, description="Question text", examples=["What is the project budget?"]
    )
    category: QuestionCategory | None = Field(None, examples=["constraints"])
    required: bool | None = Field(None, examples=[False])

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if v is not None:
            return validate_non_empty_text(v, "Question text")
        return v


class QuestionListResponse(BaseModel):
    """Response containing list of questions for a session."""

    session_id: str
    questions: list[Question]


class QuestionDetailResponse(BaseModel):
    """Response containing question details with optional answer."""

    session_id: str
    question: Question
    answer: Answer | None


# Answer CRUD schemas
class AnswerUpdateRequest(BaseModel):
    """Request to update an answer."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Answer text",
        examples=["The project must be completed within 6 months with a budget of $100,000"],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return validate_non_empty_text(v, "Answer text", max_length=5000)


class AnswerListResponse(BaseModel):
    """Response containing list of answers for a session."""

    session_id: str
    answers: list[Answer]


class AnswerDetailResponse(BaseModel):
    """Response containing answer details with associated question."""

    session_id: str
    answer: Answer
    question: Question
