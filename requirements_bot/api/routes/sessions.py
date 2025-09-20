from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.status import HTTP_201_CREATED

from requirements_bot.api.dependencies import (
    get_database_manager,
    get_session_setup_manager,
)
from requirements_bot.api.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
)
from requirements_bot.core.services import SessionSetupManager
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
    db.save_session(session)

    return SessionCreateResponse(
        id=session.id,
        project=session.project,
        conversation_state=session.conversation_state,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(db: Annotated[DatabaseManager, Depends(get_database_manager)]) -> SessionListResponse:
    """List all requirements gathering sessions."""
    summary_data = db.get_session_summaries()

    session_summaries = []
    for (
        session_id,
        project,
        conversation_state,
        conversation_complete,
        questions_count,
        answers_count,
        requirements_count,
        created_at,
        updated_at,
    ) in summary_data:
        session_summaries.append(
            SessionSummary(
                id=session_id,
                project=project,
                conversation_state=conversation_state,
                conversation_complete=conversation_complete,
                questions_count=questions_count,
                answers_count=answers_count,
                requirements_count=requirements_count,
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    return SessionListResponse(sessions=session_summaries)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str, db: Annotated[DatabaseManager, Depends(get_database_manager)]
) -> SessionDetailResponse:
    """Get detailed information about a specific session."""
    session = db.load_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

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
    session_id: str, db: Annotated[DatabaseManager, Depends(get_database_manager)]
) -> dict[str, str]:
    """Delete a specific session."""
    db.delete_session(session_id)
    return {"message": f"Session {session_id} deleted successfully"}
