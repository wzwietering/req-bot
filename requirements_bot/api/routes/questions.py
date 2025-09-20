from typing import Annotated

from fastapi import APIRouter, Depends

from requirements_bot.api.dependencies import get_database_manager, get_session_answer_service, get_validated_session_id
from requirements_bot.api.exceptions import SessionInvalidStateException, SessionNotFoundAPIException
from requirements_bot.api.schemas import (
    AnswerSubmissionResponse,
    QuestionAnswerRequest,
    SessionContinueResponse,
    SessionProgress,
    SessionStatusResponse,
)
from requirements_bot.api.utils import calculate_session_progress
from requirements_bot.core.services import SessionAnswerService
from requirements_bot.core.storage import DatabaseManager

router = APIRouter()


@router.post("/sessions/{session_id}/continue", response_model=SessionContinueResponse)
async def continue_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
) -> SessionContinueResponse:
    """Continue or resume a session to get the next question."""
    session = db.load_session(session_id)
    if not session:
        raise SessionNotFoundAPIException(session_id)

    if session.conversation_complete:
        return SessionContinueResponse(
            session_id=session.id,
            next_question=None,
            conversation_complete=True,
            conversation_state=session.conversation_state,
        )

    next_question = answer_service.get_next_unanswered_question(session)

    return SessionContinueResponse(
        session_id=session.id,
        next_question=next_question,
        conversation_complete=session.conversation_complete,
        conversation_state=session.conversation_state,
    )


def _validate_session_for_answer(session, session_id: str):
    """Validate that a session exists and can accept answers."""
    if not session:
        raise SessionNotFoundAPIException(session_id)

    if session.conversation_complete:
        raise SessionInvalidStateException("Session is already complete")


def _get_and_validate_current_question(session, answer_service: SessionAnswerService):
    """Get current question and validate it exists."""
    current_question = answer_service.get_next_unanswered_question(session)
    if not current_question:
        raise SessionInvalidStateException("No current question to answer")
    return current_question


@router.post("/sessions/{session_id}/answers", response_model=AnswerSubmissionResponse)
async def submit_answer(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    request: QuestionAnswerRequest,
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
) -> AnswerSubmissionResponse:
    """Submit an answer to the current question."""
    session = answer_service.storage.load_session(session_id)
    _validate_session_for_answer(session, session_id)

    current_question = _get_and_validate_current_question(session, answer_service)
    updated_session, is_complete = answer_service.process_answer(session, current_question, request.answer_text)
    new_answer = updated_session.answers[-1]
    requirements_generated = is_complete and len(updated_session.requirements) > 0

    return AnswerSubmissionResponse(
        session_id=updated_session.id,
        question=current_question,
        answer=new_answer,
        conversation_complete=is_complete,
        conversation_state=updated_session.conversation_state,
        requirements_generated=requirements_generated,
    )


@router.get("/sessions/{session_id}/questions/current")
async def get_current_question_endpoint(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
):
    """Get the current question for a session."""
    session = db.load_session(session_id)
    if not session:
        raise SessionNotFoundAPIException(session_id)

    if session.conversation_complete:
        return {"current_question": None, "conversation_complete": True}

    current_question = answer_service.get_next_unanswered_question(session)
    return {
        "current_question": current_question,
        "conversation_complete": session.conversation_complete,
        "conversation_state": session.conversation_state,
    }


def _calculate_session_progress_data(session) -> SessionProgress:
    """Calculate and return session progress data."""
    total_questions, answered_questions, remaining_questions, completion_percentage = calculate_session_progress(
        session
    )

    return SessionProgress(
        total_questions=total_questions,
        answered_questions=answered_questions,
        remaining_questions=remaining_questions,
        completion_percentage=completion_percentage,
    )


def _get_current_question_if_active(session, answer_service: SessionAnswerService):
    """Get current question if session is not complete."""
    if session.conversation_complete:
        return None
    return answer_service.get_next_unanswered_question(session)


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    db: Annotated[DatabaseManager, Depends(get_database_manager)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
) -> SessionStatusResponse:
    """Get the current status and progress of a session."""
    session = db.load_session(session_id)
    if not session:
        raise SessionNotFoundAPIException(session_id)

    progress = _calculate_session_progress_data(session)
    current_question = _get_current_question_if_active(session, answer_service)

    return SessionStatusResponse(
        session_id=session.id,
        conversation_state=session.conversation_state,
        conversation_complete=session.conversation_complete,
        current_question=current_question,
        progress=progress,
    )
