from unittest.mock import Mock

import pytest

from requirements_bot.core.conversation_state import (
    ConversationState,
)
from requirements_bot.core.models import Session
from requirements_bot.core.services.question_generation_service import (
    QuestionGenerationService,
)


class TestQuestionGenerationService:
    """Test the question generation service, particularly state transition bugs."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager with state manager."""
        session_manager = Mock()
        session_manager.state_manager = Mock()
        return session_manager

    @pytest.fixture
    def mock_question_queue_manager(self):
        """Mock question queue manager."""
        queue_manager = Mock()
        queue_manager.initialize_from_seeds.return_value = [{"text": "Test question", "category": "test"}]
        queue_manager.filter_asked_questions.return_value = [{"text": "New question", "category": "test"}]
        return queue_manager

    @pytest.fixture
    def mock_provider(self):
        """Mock provider."""
        return Mock()

    @pytest.fixture
    def question_service(self, mock_session_manager, mock_question_queue_manager, mock_provider):
        """Create question generation service with mocked dependencies."""
        return QuestionGenerationService(
            provider=mock_provider,
            session_manager=mock_session_manager,
            question_queue_manager=mock_question_queue_manager,
            model_id="test-model",
        )

    @pytest.fixture
    def sample_session_assessing_completeness(self):
        """Create a session in ASSESSING_COMPLETENESS state - the problematic state."""
        return Session(
            project="Test Project",
            questions=[],
            answers=[],
            requirements=[],
            conversation_state=ConversationState.ASSESSING_COMPLETENESS,
        )

    def test_generate_missing_area_questions_bug_is_fixed(
        self,
        question_service,
        sample_session_assessing_completeness,
        mock_session_manager,
    ):
        """
        Test that the issue has been fixed: method no longer attempts invalid transition.

        This test verifies that the bug fix works correctly:
        1. Session is in ASSESSING_COMPLETENESS state
        2. generate_missing_area_questions() is called
        3. Method does not attempt any state transition
        4. Questions are generated successfully
        """
        # Configure the state manager for successful operation
        mock_session_manager.state_manager.create_checkpoint.return_value = None

        # Call the method - should work without any state transition attempts
        result = question_service.generate_missing_area_questions(sample_session_assessing_completeness)

        # Verify questions were generated
        assert len(result) > 0

        # Verify that NO state transition was attempted (this was the bug)
        mock_session_manager.state_manager.transition_to.assert_not_called()

        # But checkpoint should still be created for error recovery
        mock_session_manager.state_manager.create_checkpoint.assert_called_once_with(
            sample_session_assessing_completeness, "generate_missing_area_questions"
        )

    def test_generate_missing_area_questions_should_not_transition_when_fixed(
        self,
        question_service,
        sample_session_assessing_completeness,
        mock_session_manager,
    ):
        """
        Test that after the fix, the method should work without invalid transitions.

        This test verifies the expected behavior after the fix:
        1. Session is in ASSESSING_COMPLETENESS state
        2. generate_missing_area_questions() is called
        3. Method should NOT attempt any state transition (the caller handles it)
        4. Questions are generated successfully
        """
        # Configure mocks for successful operation
        mock_session_manager.state_manager.transition_to.return_value = None
        mock_session_manager.state_manager.create_checkpoint.return_value = None

        # Mock the private method that generates questions
        question_service._generate_questions_with_fallback = Mock(
            return_value=[{"text": "Missing area question", "category": "test"}]
        )

        # Call the method - should work without state transition errors
        result = question_service.generate_missing_area_questions(sample_session_assessing_completeness)

        # Verify questions were generated (content comes from queue manager mock)
        assert len(result) > 0
        assert result[0]["text"] == "New question"

        # After the fix, this method should NOT call transition_to at all
        # The caller (completeness assessment service) handles the transition
        # This assertion will fail with current buggy code, pass after fix
        mock_session_manager.state_manager.transition_to.assert_not_called()

        # But checkpoint should still be created for error recovery
        mock_session_manager.state_manager.create_checkpoint.assert_called_once_with(
            sample_session_assessing_completeness, "generate_missing_area_questions"
        )
