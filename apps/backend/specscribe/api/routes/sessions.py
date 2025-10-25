from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from specscribe.api.dependencies import (
    enforce_question_quota,
    get_api_interview_service,
    get_current_user_id,
    get_session_service,
    get_validated_session_id,
)
from specscribe.api.exceptions import SessionNotFoundAPIException
from specscribe.api.schemas import (
    QuestionAnswerPair,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionQAResponse,
    SessionSummary,
)
from specscribe.api.services.interview_service import APIInterviewService
from specscribe.core.models import Session
from specscribe.core.services import SessionResponseBuilder, SessionService
from specscribe.core.services.session_service import SessionValidationError

router = APIRouter()


@router.post("/sessions", response_model=SessionCreateResponse, status_code=HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    interview_service: Annotated[APIInterviewService, Depends(get_api_interview_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
    _: Annotated[None, Depends(enforce_question_quota)],
) -> SessionCreateResponse:
    """Create a new requirements gathering session with LLM-generated questions."""
    session = interview_service.create_session(request.project, user_id)
    response_data = SessionResponseBuilder.build_session_create_response(session)

    return SessionCreateResponse(**response_data)


def _create_session_summary(summary_data_row) -> SessionSummary:
    """Create a SessionSummary from database row data."""
    summary_data = SessionResponseBuilder.build_session_summary(summary_data_row)
    return SessionSummary(**summary_data)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionListResponse:
    """List user's requirements gathering sessions."""
    summary_data = session_service.get_session_summaries(user_id)
    session_summaries = [_create_session_summary(row) for row in summary_data]
    return SessionListResponse(sessions=session_summaries)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionDetailResponse:
    """Get detailed information about a specific session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        response_data = SessionResponseBuilder.build_session_detail(session)
        return SessionDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.get("/sessions/{session_id}/qa", response_model=SessionQAResponse)
async def get_session_qa(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionQAResponse:
    """Get all questions and answers for a specific session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        qa_pairs = _build_qa_pairs(session)
        return SessionQAResponse(session_id=session.id, project=session.project, qa_pairs=qa_pairs)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


def _build_qa_pairs(session: Session) -> list[QuestionAnswerPair]:
    """Build question-answer pairs from session data."""
    qa_history = session.get_qa_history()
    return [QuestionAnswerPair(question=q, answer=a) for q, a in qa_history]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, str]:
    """Delete a specific session."""
    try:
        session_service.delete_session(session_id, user_id)
        return {"message": f"Session {session_id} deleted successfully"}
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)
