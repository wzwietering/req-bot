from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from requirements_bot.api.dependencies import (
    get_database_manager,
    get_session_setup_manager,
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
from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.services import SessionSetupManager
from requirements_bot.core.services.question_service import QuestionService
from requirements_bot.core.storage import DatabaseManager

router = APIRouter()


@router.post("/sessions", response_model=SessionCreateResponse, status_code=HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    setup_manager: Annotated[SessionSetupManager, Depends(get_session_setup_manager)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> SessionCreateResponse:
    """Create a new requirements gathering session."""
    session, _ = setup_manager.setup_session(request.project, None, "conversational")

    # Add basic questions for API sessions
    if not session.questions:
        session.questions = QuestionService.generate_basic_questions(request.project)
        session.conversation_state = ConversationState.WAITING_FOR_INPUT

    db.save_session(session)

    return SessionCreateResponse(
        id=session.id,
        project=session.project,
        conversation_state=session.conversation_state,
        created_at=session.created_at,
    )


def _create_session_summary(summary_data_row) -> SessionSummary:
    """Create a SessionSummary from database row data."""
    fields = [
        "id",
        "project",
        "conversation_state",
        "conversation_complete",
        "questions_count",
        "answers_count",
        "requirements_count",
        "created_at",
        "updated_at",
    ]
    return SessionSummary(**dict(zip(fields, summary_data_row, strict=False)))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(db: Annotated[DatabaseManager, Depends(get_database_manager)]) -> SessionListResponse:
    """List all requirements gathering sessions."""
    summary_data = db.get_session_summaries()
    session_summaries = [_create_session_summary(row) for row in summary_data]
    return SessionListResponse(sessions=session_summaries)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> SessionDetailResponse:
    """Get detailed information about a specific session."""
    session = db.load_session(session_id)
    if not session:
        raise SessionNotFoundAPIException(session_id)

    return SessionDetailResponse(
        id=session.id,
        project=session.project,
        questions=session.questions,
        answers=session.answers,
        requirements=session.requirements,
        conversation_complete=session.conversation_complete,
        conversation_state=session.conversation_state,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> dict[str, str]:
    """Delete a specific session."""
    db.delete_session(session_id)
    return {"message": f"Session {session_id} deleted successfully"}
