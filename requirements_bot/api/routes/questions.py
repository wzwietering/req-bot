from typing import Annotated

from fastapi import APIRouter, Depends

from requirements_bot.api.dependencies import (
    get_session_answer_service,
    get_session_service,
    get_validated_session_id,
)
from requirements_bot.api.exceptions import SessionInvalidStateException, SessionNotFoundAPIException
from requirements_bot.api.schemas import (
    AnswerSubmissionResponse,
    QuestionAnswerRequest,
    SessionContinueResponse,
    SessionStatusResponse,
)
from requirements_bot.core.services import SessionAnswerService, SessionResponseBuilder, SessionService
from requirements_bot.core.services.session_service import SessionValidationError

router = APIRouter()


@router.post("/sessions/{session_id}/continue", response_model=SessionContinueResponse)
async def continue_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
) -> SessionContinueResponse:
    """Continue or resume a session to get the next question."""
    try:
        session = session_service.load_session_with_validation(session_id)

        if session.conversation_complete:
            response_data = SessionResponseBuilder.build_session_continue_response(session, None, True)
        else:
            next_question = answer_service.get_next_unanswered_question(session)
            response_data = SessionResponseBuilder.build_session_continue_response(
                session, next_question, session.conversation_complete
            )

        return SessionContinueResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


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
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
) -> AnswerSubmissionResponse:
    """Submit an answer to the current question."""
    try:
        session = session_service.load_session_with_validation(session_id)
        _validate_session_for_answer(session, session_id)

        current_question = _get_and_validate_current_question(session, answer_service)
        updated_session, is_complete = answer_service.process_answer(session, current_question, request.answer_text)

        if not updated_session.answers:
            raise SessionInvalidStateException("No answers found after processing")

        new_answer = updated_session.answers[-1]
        requirements_generated = is_complete and len(updated_session.requirements) > 0

        response_data = SessionResponseBuilder.build_answer_submission_response(
            updated_session, current_question, new_answer, is_complete, requirements_generated
        )
        return AnswerSubmissionResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.get("/sessions/{session_id}/questions/current")
async def get_current_question_endpoint(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
):
    """Get the current question for a session."""
    try:
        session = session_service.load_session_with_validation(session_id)

        if session.conversation_complete:
            return {"current_question": None, "conversation_complete": True}

        current_question = answer_service.get_next_unanswered_question(session)
        return {
            "current_question": current_question,
            "conversation_complete": session.conversation_complete,
            "conversation_state": session.conversation_state,
        }
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


# Progress calculation is now handled by SessionResponseBuilder


def _get_current_question_if_active(session, answer_service: SessionAnswerService):
    """Get current question if session is not complete."""
    if session.conversation_complete:
        return None
    return answer_service.get_next_unanswered_question(session)


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> SessionStatusResponse:
    """Get the current status and progress of a session."""
    try:
        session = session_service.load_session_with_validation(session_id)

        progress_data = session_service.get_session_progress(session)
        current_question = _get_current_question_if_active(session, answer_service)

        response_data = SessionResponseBuilder.build_session_status_response(session, progress_data, current_question)
        return SessionStatusResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)
