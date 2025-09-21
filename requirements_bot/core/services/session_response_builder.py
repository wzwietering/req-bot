"""Session response builders for unified API response construction.

This module provides utilities to build consistent API responses from session data,
reducing duplication between different API endpoints.
"""

from requirements_bot.core.models import Session


class SessionResponseBuilder:
    """Builds consistent API responses from session data."""

    @staticmethod
    def build_session_summary(summary_data_row) -> dict:
        """Create a session summary dictionary from database row data.

        Args:
            summary_data_row: Raw session summary data from storage

        Returns:
            dict: Formatted session summary
        """
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
        return dict(zip(fields, summary_data_row, strict=False))

    @staticmethod
    def build_session_detail(session: Session) -> dict:
        """Create a detailed session response from session object.

        Args:
            session: The session object

        Returns:
            dict: Formatted session detail response
        """
        return {
            "id": session.id,
            "project": session.project,
            "questions": session.questions,
            "answers": session.answers,
            "requirements": session.requirements,
            "conversation_complete": session.conversation_complete,
            "conversation_state": session.conversation_state,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    @staticmethod
    def build_session_create_response(session: Session) -> dict:
        """Create a session creation response from session object.

        Args:
            session: The newly created session

        Returns:
            dict: Formatted session creation response
        """
        return {
            "id": session.id,
            "project": session.project,
            "conversation_state": session.conversation_state,
            "created_at": session.created_at,
        }

    @staticmethod
    def build_session_continue_response(
        session: Session, next_question=None, conversation_complete: bool = None
    ) -> dict:
        """Create a session continue response.

        Args:
            session: The session object
            next_question: Next question object (if any)
            conversation_complete: Override conversation complete status

        Returns:
            dict: Formatted session continue response
        """
        complete = conversation_complete if conversation_complete is not None else session.conversation_complete

        return {
            "session_id": session.id,
            "next_question": next_question,
            "conversation_complete": complete,
            "conversation_state": session.conversation_state,
        }

    @staticmethod
    def build_session_status_response(session: Session, progress_data: dict, current_question=None) -> dict:
        """Create a session status response.

        Args:
            session: The session object
            progress_data: Progress metrics from SessionService
            current_question: Current question object (if any)

        Returns:
            dict: Formatted session status response
        """
        return {
            "session_id": session.id,
            "conversation_state": session.conversation_state,
            "conversation_complete": session.conversation_complete,
            "current_question": current_question,
            "progress": {
                "total_questions": progress_data["total_questions"],
                "answered_questions": progress_data["answered_questions"],
                "remaining_questions": progress_data["remaining_questions"],
                "completion_percentage": progress_data["completion_percentage"],
            },
        }

    @staticmethod
    def build_answer_submission_response(
        session: Session, question, answer, is_complete: bool, requirements_generated: bool = False
    ) -> dict:
        """Create an answer submission response.

        Args:
            session: The updated session
            question: The question object that was answered
            answer: The answer object that was submitted
            is_complete: Whether the conversation is complete
            requirements_generated: Whether requirements were generated

        Returns:
            dict: Formatted answer submission response
        """
        return {
            "session_id": session.id,
            "question": question,
            "answer": answer,
            "conversation_complete": is_complete,
            "conversation_state": session.conversation_state,
            "requirements_generated": requirements_generated,
        }
