from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from requirements_bot.api.dependencies import (
    get_session_service,
    get_validated_session_id,
)
from requirements_bot.api.exceptions import SessionNotFoundAPIException
from requirements_bot.api.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
)
from requirements_bot.core.services import SessionResponseBuilder, SessionService
from requirements_bot.core.services.session_service import SessionValidationError

router = APIRouter()


@router.post("/sessions", response_model=SessionCreateResponse, status_code=HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionCreateResponse:
    """Create a new requirements gathering session."""
    session = session_service.get_or_create_session(request.project)
    response_data = SessionResponseBuilder.build_session_create_response(session)

    return SessionCreateResponse(**response_data)


def _create_session_summary(summary_data_row) -> SessionSummary:
    """Create a SessionSummary from database row data."""
    summary_data = SessionResponseBuilder.build_session_summary(summary_data_row)
    return SessionSummary(**summary_data)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionListResponse:
    """List all requirements gathering sessions."""
    summary_data = session_service.get_session_summaries()
    session_summaries = [_create_session_summary(row) for row in summary_data]
    return SessionListResponse(sessions=session_summaries)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionDetailResponse:
    """Get detailed information about a specific session."""
    try:
        session = session_service.load_session_with_validation(session_id)
        response_data = SessionResponseBuilder.build_session_detail(session)
        return SessionDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> dict[str, str]:
    """Delete a specific session."""
    try:
        session_service.delete_session(session_id)
        return {"message": f"Session {session_id} deleted successfully"}
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)
