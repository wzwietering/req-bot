from unittest.mock import Mock

import pytest

from requirements_bot.core.conversation_state import (
    ConversationState,
    StateTransitionError,
)
from requirements_bot.core.models import Session
from requirements_bot.core.state_manager import ConversationStateManager


class TestConversationStateManager:
    """Test the conversation state manager."""

    @pytest.fixture
    def mock_storage(self):
        return Mock()

    @pytest.fixture
    def state_manager(self, mock_storage):
        return ConversationStateManager(mock_storage)

    @pytest.fixture
    def sample_session(self):
        return Session(
            project="Test Project",
            questions=[],
            answers=[],
            requirements=[],
            conversation_state=ConversationState.INITIALIZING,
        )

    def test_valid_state_transition(self, state_manager, sample_session, mock_storage):
        """Test that valid state transitions work."""
        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS)

        assert sample_session.conversation_state == ConversationState.GENERATING_QUESTIONS
        assert mock_storage.save_session.called

    def test_invalid_state_transition(self, state_manager, sample_session):
        """Test that invalid state transitions raise errors."""
        with pytest.raises(StateTransitionError):
            state_manager.transition_to(sample_session, ConversationState.PROCESSING_ANSWER)

    def test_context_updates(self, state_manager, sample_session, mock_storage):
        """Test that context updates work during transitions."""
        context_updates = {"current_question_index": 5, "llm_operation_id": "test_op"}

        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS, context_updates)

        assert sample_session.state_context.current_question_index == 5
        assert sample_session.state_context.llm_operation_id == "test_op"

    def test_checkpoint_creation(self, state_manager, sample_session, mock_storage):
        """Test checkpoint creation before risky operations."""
        state_manager.create_checkpoint(sample_session, "test_operation")

        assert sample_session.state_context.llm_operation_id == "test_operation"
        assert mock_storage.save_session.called

    def test_can_recover_from_interruption(self, state_manager, sample_session):
        """Test recovery capability detection."""
        # Non-terminal states can recover
        sample_session.conversation_state = ConversationState.WAITING_FOR_INPUT
        assert state_manager.can_recover_from_interruption(sample_session)

        # Terminal states cannot recover
        sample_session.conversation_state = ConversationState.COMPLETED
        assert not state_manager.can_recover_from_interruption(sample_session)

    def test_determine_recovery_action(self, state_manager, sample_session):
        """Test recovery action determination."""
        test_cases = [
            (ConversationState.INITIALIZING, "restart_initialization"),
            (ConversationState.GENERATING_QUESTIONS, "retry_question_generation"),
            (ConversationState.WAITING_FOR_INPUT, "continue_from_question"),
            (ConversationState.PROCESSING_ANSWER, "reprocess_last_answer"),
            (ConversationState.GENERATING_FOLLOWUPS, "skip_followups_continue"),
            (ConversationState.ASSESSING_COMPLETENESS, "assume_incomplete_continue"),
            (
                ConversationState.GENERATING_REQUIREMENTS,
                "retry_requirements_generation",
            ),
        ]

        for state, expected_action in test_cases:
            sample_session.conversation_state = state
            action = state_manager.determine_recovery_action(sample_session)
            assert action == expected_action

    def test_storage_error_handling(self, mock_storage, sample_session):
        """Test that storage errors are handled gracefully."""
        mock_storage.save_session.side_effect = Exception("Storage error")
        state_manager = ConversationStateManager(mock_storage)

        # Should not raise exception, just print warning
        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS)
        assert sample_session.conversation_state == ConversationState.GENERATING_QUESTIONS

    def test_no_storage_manager(self, sample_session):
        """Test state manager works without storage."""
        state_manager = ConversationStateManager(None)

        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS)
        assert sample_session.conversation_state == ConversationState.GENERATING_QUESTIONS
