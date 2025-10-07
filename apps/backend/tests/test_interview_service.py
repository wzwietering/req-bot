from unittest.mock import Mock, patch

import pytest

from requirements_bot.api.services.interview_service import APIInterviewService
from requirements_bot.core.conversation_state import (
    ConversationState,
)
from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.services.completeness_assessment_service import (
    CompletenessAssessmentService,
)


class TestInterviewServiceStateTransitions:
    """Test state transition handling in interview service."""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        storage = Mock()
        storage.save_session = Mock()
        storage.load_session = Mock()
        return storage

    @pytest.fixture
    def interview_service(self, mock_storage):
        """Create interview service with mock storage."""
        return APIInterviewService(storage=mock_storage, model_id="test-model")

    @pytest.fixture
    def session_in_assessing_completeness(self):
        """Create a session stuck in ASSESSING_COMPLETENESS state."""
        session = Session(
            user_id="test-user",
            project="Test Project",
            questions=[
                Question(id="q1", text="Question 1?", category="scope", required=True),
                Question(id="q2", text="Question 2?", category="users", required=True),
            ],
            answers=[
                Answer(question_id="q1", text="Answer 1"),
            ],
            requirements=[],
            conversation_state=ConversationState.ASSESSING_COMPLETENESS,
            conversation_complete=False,
        )
        return session

    @pytest.fixture
    def session_with_all_questions_answered(self):
        """Create session with all questions answered."""
        session = Session(
            user_id="test-user",
            project="Test Project",
            questions=[
                Question(id="q1", text="Question 1?", category="scope", required=True),
                Question(id="q2", text="Question 2?", category="users", required=True),
            ],
            answers=[
                Answer(question_id="q1", text="Answer 1"),
                Answer(question_id="q2", text="Answer 2"),
            ],
            requirements=[],
            conversation_state=ConversationState.WAITING_FOR_INPUT,
            conversation_complete=False,
        )
        return session

    @pytest.fixture
    def session_with_unanswered_questions(self):
        """Create session with unanswered questions."""
        session = Session(
            user_id="test-user",
            project="Test Project",
            questions=[
                Question(id="q1", text="Question 1?", category="scope", required=True),
                Question(id="q2", text="Question 2?", category="users", required=True),
            ],
            answers=[
                Answer(question_id="q1", text="Answer 1"),
            ],
            requirements=[],
            conversation_state=ConversationState.WAITING_FOR_INPUT,
            conversation_complete=False,
        )
        return session

    def test_process_answer_when_stuck_in_assessing_completeness(
        self, interview_service, mock_storage, session_in_assessing_completeness
    ):
        """Test that process_answer handles session stuck in ASSESSING_COMPLETENESS.

        This is the main bug: when a session is in ASSESSING_COMPLETENESS and
        process_answer is called, it should recover gracefully instead of
        raising StateTransitionError.
        """
        mock_storage.load_session.return_value = session_in_assessing_completeness

        # Mock the pipeline components to prevent actual LLM calls
        with patch(
            "requirements_bot.api.services.interview_service.ConversationalInterviewPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline

            # Mock the state manager
            mock_state_manager = Mock()
            mock_pipeline.session_manager.state_manager = mock_state_manager

            # Mock conductor to prevent LLM calls
            mock_pipeline.conductor.analyze_response = Mock(
                return_value=Mock(follow_up_questions=[], needs_clarification=False)
            )
            mock_pipeline.conductor.log_answer_received = Mock()
            mock_pipeline.conductor.update_answer_metadata = Mock()
            mock_pipeline.question_generation.generate_next_question_if_needed = Mock(return_value=None)
            mock_pipeline.completeness_assessment.should_check_completeness = Mock(return_value=False)

            # This should NOT raise StateTransitionError
            # It should recover by transitioning to WAITING_FOR_INPUT first
            _ = interview_service.process_answer(
                session_id=session_in_assessing_completeness.id, answer_text="Answer 2"
            )

            # Verify state transition happened correctly
            # Should transition to WAITING_FOR_INPUT first, then to PROCESSING_ANSWER
            assert mock_state_manager.transition_to.called
            calls = mock_state_manager.transition_to.call_args_list

            # First call should be WAITING_FOR_INPUT (recovery from ASSESSING_COMPLETENESS)
            assert calls[0][0][1] == ConversationState.WAITING_FOR_INPUT
            # Second call should be PROCESSING_ANSWER
            assert calls[1][0][1] == ConversationState.PROCESSING_ANSWER

    def test_process_answer_normal_flow(self, interview_service, mock_storage, session_with_unanswered_questions):
        """Test normal answer processing when in WAITING_FOR_INPUT state."""
        mock_storage.load_session.return_value = session_with_unanswered_questions

        with patch(
            "requirements_bot.api.services.interview_service.ConversationalInterviewPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline

            mock_state_manager = Mock()
            mock_pipeline.session_manager.state_manager = mock_state_manager

            mock_pipeline.conductor.analyze_response = Mock(
                return_value=Mock(follow_up_questions=[], needs_clarification=False)
            )
            mock_pipeline.conductor.log_answer_received = Mock()
            mock_pipeline.conductor.update_answer_metadata = Mock()
            mock_pipeline.question_generation.generate_next_question_if_needed = Mock(return_value=None)
            mock_pipeline.completeness_assessment.should_check_completeness = Mock(return_value=False)

            _ = interview_service.process_answer(
                session_id=session_with_unanswered_questions.id, answer_text="Answer 2"
            )

            # Should directly transition to PROCESSING_ANSWER (no recovery needed)
            mock_state_manager.transition_to.assert_any_call(
                session_with_unanswered_questions, ConversationState.PROCESSING_ANSWER
            )

    def test_assess_and_finalize_with_stuck_state(
        self, interview_service, mock_storage, session_in_assessing_completeness
    ):
        """Test that _assess_and_finalize handles sessions already in assessment state."""
        mock_storage.load_session.return_value = session_in_assessing_completeness

        with patch(
            "requirements_bot.api.services.interview_service.ConversationalInterviewPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline

            mock_state_manager = Mock()
            mock_pipeline.session_manager.state_manager = mock_state_manager

            mock_pipeline.completeness_assessment.assess_and_handle_completeness = Mock()
            mock_pipeline.finalize_session = Mock(return_value=session_in_assessing_completeness)

            # Should handle the case where we're already in ASSESSING_COMPLETENESS
            result = interview_service._assess_and_finalize(session_in_assessing_completeness, mock_pipeline)

            # Should still work without raising errors
            assert result is not None


class TestCompletenessAssessmentErrorHandling:
    """Test error handling in completeness assessment."""

    @pytest.fixture
    def mock_storage(self):
        storage = Mock()
        storage.save_session = Mock()
        return storage

    @pytest.fixture
    def mock_conductor(self):
        return Mock()

    @pytest.fixture
    def mock_session_manager(self, mock_storage):
        manager = Mock()
        manager.storage = mock_storage
        manager.state_manager = Mock()
        return manager

    @pytest.fixture
    def mock_question_generation(self):
        return Mock()

    @pytest.fixture
    def completeness_service(self, mock_conductor, mock_session_manager, mock_question_generation):
        """Create completeness assessment service with mocks."""

        return CompletenessAssessmentService(
            conductor=mock_conductor,
            session_manager=mock_session_manager,
            question_generation_service=mock_question_generation,
            model_id="test-model",
        )

    @pytest.fixture
    def sample_session(self):
        return Session(
            user_id="test-user",
            project="Test Project",
            questions=[
                Question(id="q1", text="Question 1?", category="scope", required=True),
            ],
            answers=[
                Answer(question_id="q1", text="Answer 1"),
            ],
            requirements=[],
            conversation_state=ConversationState.PROCESSING_ANSWER,
            conversation_complete=False,
        )

    def test_assess_handles_llm_failure(self, completeness_service, mock_conductor, sample_session):
        """Test that assessment handles LLM failures gracefully.

        When the LLM call fails, the service should:
        1. Catch the exception
        2. Transition back to WAITING_FOR_INPUT
        3. Log the error
        4. NOT leave the session stuck in ASSESSING_COMPLETENESS
        """
        # Simulate LLM failure
        mock_conductor.assess_interview_status.side_effect = Exception("LLM timeout or error")

        # This should NOT raise exception
        # It should handle the error and transition to WAITING_FOR_INPUT
        question_queue = []

        # Should not raise - error should be caught and handled
        _ = completeness_service.assess_and_handle_completeness(sample_session, question_queue)

        # Should transition to WAITING_FOR_INPUT even after error
        completeness_service.session_manager.state_manager.transition_to.assert_any_call(
            sample_session, ConversationState.WAITING_FOR_INPUT
        )

    def test_assess_handles_incomplete_result(self, completeness_service, mock_conductor, sample_session):
        """Test that assessment properly handles incomplete interview."""
        # Mock assessment returning incomplete
        mock_completeness = Mock()
        mock_completeness.is_complete = False
        mock_conductor.assess_interview_status.return_value = mock_completeness

        question_queue = []
        completeness_service.assess_and_handle_completeness(sample_session, question_queue)

        # Should transition back to WAITING_FOR_INPUT
        completeness_service.session_manager.state_manager.transition_to.assert_called_with(
            sample_session, ConversationState.WAITING_FOR_INPUT
        )
        # Should NOT mark as complete
        assert sample_session.conversation_complete is False

    def test_assess_handles_complete_result(self, completeness_service, mock_conductor, sample_session):
        """Test that assessment properly handles complete interview."""
        # Mock assessment returning complete
        mock_completeness = Mock()
        mock_completeness.is_complete = True
        mock_conductor.assess_interview_status.return_value = mock_completeness

        question_queue = []
        completeness_service.assess_and_handle_completeness(sample_session, question_queue)

        # Should mark session as complete
        assert sample_session.conversation_complete is True
        # Should NOT transition to WAITING_FOR_INPUT
        # (stays in ASSESSING_COMPLETENESS for requirements generation)


class TestEndToEndStateFlow:
    """Integration tests for complete state flow."""

    @pytest.fixture
    def mock_storage(self):
        storage = Mock()
        storage.save_session = Mock()
        storage.load_session = Mock()
        return storage

    @pytest.fixture
    def interview_service(self, mock_storage):
        return APIInterviewService(storage=mock_storage, model_id="test-model")

    def test_full_workflow_with_completeness_check(self, interview_service, mock_storage):
        """Test complete workflow: answer → assessment triggered → completion.

        This tests the full state flow:
        WAITING_FOR_INPUT → PROCESSING_ANSWER → ASSESSING_COMPLETENESS → WAITING_FOR_INPUT
        """
        session = Session(
            user_id="test-user",
            project="Test Project",
            questions=[
                Question(id="q1", text="Question 1?", category="scope", required=True),
            ],
            answers=[],
            requirements=[],
            conversation_state=ConversationState.WAITING_FOR_INPUT,
            conversation_complete=False,
        )
        mock_storage.load_session.return_value = session

        with patch(
            "requirements_bot.api.services.interview_service.ConversationalInterviewPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline

            mock_state_manager = Mock()
            mock_pipeline.session_manager.state_manager = mock_state_manager

            # Mock successful assessment that returns incomplete
            mock_completeness = Mock()
            mock_completeness.is_complete = False

            mock_pipeline.conductor.analyze_response = Mock(
                return_value=Mock(follow_up_questions=[], needs_clarification=False)
            )
            mock_pipeline.conductor.log_answer_received = Mock()
            mock_pipeline.conductor.update_answer_metadata = Mock()
            mock_pipeline.conductor.assess_interview_status = Mock(return_value=mock_completeness)
            mock_pipeline.conductor.handle_missing_areas = Mock()

            mock_pipeline.question_generation.generate_next_question_if_needed = Mock(return_value=None)
            mock_pipeline.completeness_assessment.should_check_completeness = Mock(
                return_value=True  # Trigger assessment
            )
            mock_pipeline.completeness_assessment.assess_and_handle_completeness = Mock()

            # Process an answer that triggers completeness check
            _ = interview_service.process_answer(session_id=session.id, answer_text="Final answer")

            # Verify assessment was triggered
            assert mock_pipeline.completeness_assessment.assess_and_handle_completeness.called
