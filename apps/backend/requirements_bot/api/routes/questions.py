from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from requirements_bot.api.dependencies import (
    check_retry_rate_limit,
    get_api_interview_service,
    get_current_user_id,
    get_session_answer_service,
    get_session_service,
    get_validated_session_id,
)
from requirements_bot.api.exceptions import SessionInvalidStateException, SessionNotFoundAPIException
from requirements_bot.api.schemas import (
    AnswerSubmissionResponse,
    QuestionAnswerRequest,
    RetryRequirementsResponse,
    SessionContinueResponse,
    SessionStatusResponse,
)
from requirements_bot.api.services.interview_service import APIInterviewService
from requirements_bot.core.logging import log_event
from requirements_bot.core.services import SessionAnswerService, SessionResponseBuilder, SessionService
from requirements_bot.core.services.session_service import SessionValidationError
from requirements_bot.providers.exceptions import OverloadedError

router = APIRouter()


@router.post("/sessions/{session_id}/continue", response_model=SessionContinueResponse)
async def continue_session(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    interview_service: Annotated[APIInterviewService, Depends(get_api_interview_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionContinueResponse:
    """Continue or resume a session to get the next question."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        next_question = interview_service.get_next_question(session)
        is_complete = session.conversation_complete

        response_data = SessionResponseBuilder.build_session_continue_response(session, next_question, is_complete)

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
    interview_service: Annotated[APIInterviewService, Depends(get_api_interview_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AnswerSubmissionResponse:
    """Submit an answer using intelligent pipeline logic."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        _validate_session_for_answer(session, session_id)

        updated_session = interview_service.process_answer(session_id, request.answer_text)

        if not updated_session.answers:
            raise SessionInvalidStateException("No answers found after processing")

        new_answer = updated_session.answers[-1]
        # Find the question that was just answered
        answered_question = next((q for q in updated_session.questions if q.id == new_answer.question_id), None)
        if not answered_question:
            raise SessionInvalidStateException("Could not find question for submitted answer")

        is_complete = updated_session.conversation_complete
        requirements_generated = is_complete and len(updated_session.requirements) > 0

        response_data = SessionResponseBuilder.build_answer_submission_response(
            updated_session, answered_question, new_answer, is_complete, requirements_generated
        )
        return AnswerSubmissionResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.get("/sessions/{session_id}/questions/current")
async def get_current_question_endpoint(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[SessionAnswerService, Depends(get_session_answer_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    """Get the current question for a session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

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
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> SessionStatusResponse:
    """Get the current status and progress of a session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        progress_data = session_service.get_session_progress(session)
        current_question = _get_current_question_if_active(session, answer_service)

        response_data = SessionResponseBuilder.build_session_status_response(session, progress_data, current_question)
        return SessionStatusResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.post(
    "/sessions/{session_id}/retry-requirements",
    response_model=RetryRequirementsResponse,
    dependencies=[Depends(check_retry_rate_limit)],
)
async def retry_requirements_generation(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    interview_service: Annotated[APIInterviewService, Depends(get_api_interview_service)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> RetryRequirementsResponse:
    """Retry requirements generation for a failed session.

    Rate limit: 3 attempts per 10 minutes per session to prevent abuse.
    """
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        # Retry the finalization process
        updated_session = interview_service.retry_finalization(session)

        return RetryRequirementsResponse(
            message="Requirements generation retried",
            session_id=session_id,
            requirements_count=len(updated_session.requirements),
            conversation_state=updated_session.conversation_state,
        )
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)
    except OverloadedError as e:
        log_event(
            "retry_requirements.overloaded_error",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=503,
            detail="AI service is currently overloaded. Please try again in a few moments.",
        )
    except ValidationError as e:
        log_event(
            "retry_requirements.validation_error",
            session_id=session_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Requirements generation failed due to validation error. Please contact support.",
        )
    except Exception as e:
        log_event(
            "retry_requirements.unexpected_error",
            session_id=session_id,
            user_id=user_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during retry. Please try again later."
        )
