from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from specscribe.api.dependencies import (
    check_crud_rate_limit,
    check_retry_rate_limit,
    get_answer_crud_service,
    get_api_interview_service,
    get_current_user_id,
    get_question_crud_service,
    get_session_answer_service,
    get_session_service,
    get_validated_session_id,
)
from specscribe.api.error_handlers import (
    handle_data_error,
    handle_overloaded_error,
    handle_unexpected_error,
    handle_validation_error,
)
from specscribe.api.exceptions import (
    AnswerNotFoundException,
    QuestionNotFoundException,
    SessionInvalidStateException,
    SessionNotFoundAPIException,
)
from specscribe.api.schemas import (
    AnswerDetailResponse,
    AnswerListResponse,
    AnswerSubmissionResponse,
    AnswerUpdateRequest,
    QuestionAnswerRequest,
    QuestionCreateRequest,
    QuestionDetailResponse,
    QuestionListResponse,
    RetryRequirementsResponse,
    SessionContinueResponse,
    SessionStatusResponse,
)
from specscribe.api.services.interview_service import APIInterviewService
from specscribe.core.logging import log_event
from specscribe.core.services import (
    AnswerCRUDService,
    AnswerNotFoundError,
    QuestionCRUDService,
    QuestionNotFoundError,
    SessionAnswerService,
    SessionCompleteError,
    SessionResponseBuilder,
    SessionService,
)
from specscribe.core.services.session_service import SessionValidationError
from specscribe.providers.exceptions import OverloadedError

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

        next_question, updated_session = interview_service.get_next_question(session)
        is_complete = updated_session.conversation_complete

        response_data = SessionResponseBuilder.build_session_continue_response(
            updated_session, next_question, is_complete
        )

        return SessionContinueResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


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

        if session.conversation_complete:
            raise SessionInvalidStateException("Session is already complete")

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
        current_question = (
            None if session.conversation_complete else answer_service.get_next_unanswered_question(session)
        )

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

    Rate limit: 5 attempts per 10 minutes per session to prevent abuse.
    """
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
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
        handle_overloaded_error(e, session_id, user_id)
    except ValidationError as e:
        handle_validation_error(e, session_id, user_id)
    except (KeyError, TypeError, ValueError) as e:
        handle_data_error(e, session_id, user_id)
    except Exception as e:
        handle_unexpected_error(e, session_id, user_id)


# Question CRUD endpoints
@router.get("/sessions/{session_id}/questions", response_model=QuestionListResponse)
async def list_questions(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> QuestionListResponse:
    """List all questions for a session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        response_data = SessionResponseBuilder.build_question_list_response(session)
        return QuestionListResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.get("/sessions/{session_id}/questions/{question_id}", response_model=QuestionDetailResponse)
async def get_question(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    question_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    question_service: Annotated[QuestionCRUDService, Depends(get_question_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> QuestionDetailResponse:
    """Get details of a specific question with its answer if available."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        question = question_service.get_question(session, question_id)

        if not question:
            raise QuestionNotFoundException(question_id)

        answer = question_service.get_answer_for_question(session, question_id)
        response_data = SessionResponseBuilder.build_question_detail_response(session, question, answer)
        return QuestionDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.post(
    "/sessions/{session_id}/questions",
    response_model=QuestionDetailResponse,
    status_code=201,
    dependencies=[Depends(check_crud_rate_limit)],
)
async def create_question(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    request: QuestionCreateRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    question_service: Annotated[QuestionCRUDService, Depends(get_question_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> QuestionDetailResponse:
    """Create a new question for a session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        try:
            updated_session, new_question = question_service.create_question(
                session, request.text, request.category, request.required
            )
            log_event(
                "question.created",
                session_id=session_id,
                question_id=new_question.id,
                user_id=user_id,
                category=request.category,
            )
        except SessionCompleteError as e:
            raise SessionInvalidStateException(str(e)) from e

        response_data = SessionResponseBuilder.build_question_detail_response(updated_session, new_question, None)
        return QuestionDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.delete(
    "/sessions/{session_id}/questions/{question_id}",
    dependencies=[Depends(check_crud_rate_limit)],
)
async def delete_question(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    question_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    question_service: Annotated[QuestionCRUDService, Depends(get_question_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, str]:
    """Delete a question and its associated answer."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        try:
            question_service.delete_question(session, question_id)
            log_event(
                "question.deleted",
                session_id=session_id,
                question_id=question_id,
                user_id=user_id,
            )
        except SessionCompleteError as e:
            raise SessionInvalidStateException(str(e)) from e
        except QuestionNotFoundError as e:
            raise QuestionNotFoundException(question_id) from e

        return {"message": f"Question {question_id} deleted successfully"}
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


# Answer CRUD endpoints
@router.get("/sessions/{session_id}/answers", response_model=AnswerListResponse)
async def list_answers(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AnswerListResponse:
    """List all answers for a session."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        response_data = SessionResponseBuilder.build_answer_list_response(session)
        return AnswerListResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.get("/sessions/{session_id}/answers/{question_id}", response_model=AnswerDetailResponse)
async def get_answer(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    question_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[AnswerCRUDService, Depends(get_answer_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AnswerDetailResponse:
    """Get details of a specific answer by question ID."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)
        answer = answer_service.get_answer_by_question_id(session, question_id)

        if not answer:
            raise AnswerNotFoundException(question_id)

        question = answer_service.get_question_for_answer(session, question_id)
        if not question:
            raise QuestionNotFoundException(question_id)

        response_data = SessionResponseBuilder.build_answer_detail_response(session, answer, question)
        return AnswerDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.put(
    "/sessions/{session_id}/answers/{question_id}",
    response_model=AnswerDetailResponse,
    dependencies=[Depends(check_crud_rate_limit)],
)
async def update_answer(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    question_id: str,
    request: AnswerUpdateRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[AnswerCRUDService, Depends(get_answer_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AnswerDetailResponse:
    """Update an existing answer."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        try:
            updated_session, updated_answer = answer_service.update_answer(session, question_id, request.text)
            log_event(
                "answer.updated",
                session_id=session_id,
                question_id=question_id,
                user_id=user_id,
            )
        except SessionCompleteError as e:
            raise SessionInvalidStateException(str(e)) from e
        except AnswerNotFoundError as e:
            raise AnswerNotFoundException(question_id) from e

        question = answer_service.get_question_for_answer(updated_session, question_id)
        if not question:
            raise QuestionNotFoundException(question_id)

        response_data = SessionResponseBuilder.build_answer_detail_response(updated_session, updated_answer, question)
        return AnswerDetailResponse(**response_data)
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)


@router.delete(
    "/sessions/{session_id}/answers/{question_id}",
    dependencies=[Depends(check_crud_rate_limit)],
)
async def delete_answer(
    session_id: Annotated[str, Depends(get_validated_session_id)],
    question_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
    answer_service: Annotated[AnswerCRUDService, Depends(get_answer_crud_service)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict[str, str]:
    """Delete an answer, marking the question as unanswered."""
    try:
        session = session_service.load_session_with_validation(session_id, user_id)

        try:
            answer_service.delete_answer(session, question_id)
            log_event(
                "answer.deleted",
                session_id=session_id,
                question_id=question_id,
                user_id=user_id,
            )
        except SessionCompleteError as e:
            raise SessionInvalidStateException(str(e)) from e
        except AnswerNotFoundError as e:
            raise AnswerNotFoundException(question_id) from e

        return {"message": f"Answer for question {question_id} deleted successfully"}
    except SessionValidationError:
        raise SessionNotFoundAPIException(session_id)
