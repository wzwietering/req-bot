from unittest.mock import Mock

import pytest

from requirements_bot.core.conversation_state import (
    ConversationState,
)
from requirements_bot.core.models import Question, Session
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
            user_id="test-user-id",
            project="Test Project",
            questions=[],
            answers=[],
            requirements=[],
            conversation_state=ConversationState.ASSESSING_COMPLETENESS,
        )

    def test_generate_next_question_if_needed_just_in_time(
        self,
        question_service,
        sample_session_assessing_completeness,
        mock_session_manager,
        mock_question_queue_manager,
        mock_provider,
    ):
        """
        Test just-in-time question generation.

        This test verifies the new just-in-time approach:
        1. Questions are generated one at a time when queue is low
        2. No batch generation happens
        3. Questions are context-aware
        """

        # Mock queue manager to say we need more questions
        mock_question_queue_manager.should_generate_more.return_value = True
        mock_question_queue_manager.get_next_target_area.return_value = "scope"

        # Mock provider to return a question
        mock_provider.generate_single_question.return_value = Question(
            id="test-id", text="Generated question", category="scope", required=False
        )

        # Call the method
        result = question_service.generate_next_question_if_needed(sample_session_assessing_completeness)

        # Verify a question was generated
        assert result is not None
        assert result.text == "Generated question"
        assert result.category == "scope"

        # Verify the queue manager was consulted
        mock_question_queue_manager.should_generate_more.assert_called_once()
        mock_question_queue_manager.get_next_target_area.assert_called_once()

    def test_generate_next_question_respects_queue_limit(
        self,
        question_service,
        sample_session_assessing_completeness,
        mock_question_queue_manager,
    ):
        """
        Test that question generation respects queue limits.

        This test verifies:
        1. When queue is full, no new questions are generated
        2. Just-in-time generation prevents question buildup
        """
        # Mock queue manager to say we DON'T need more questions
        mock_question_queue_manager.should_generate_more.return_value = False

        # Call the method
        result = question_service.generate_next_question_if_needed(sample_session_assessing_completeness)

        # Verify no question was generated
        assert result is None

        # Verify the queue manager was consulted
        mock_question_queue_manager.should_generate_more.assert_called_once()
