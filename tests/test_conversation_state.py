import pytest
from datetime import UTC, datetime

from requirements_bot.core.conversation_state import (
    ConversationState,
    StateContext,
    StateTransitionError,
    validate_transition,
    is_terminal_state,
    can_recover_from_state,
)


class TestConversationState:
    """Test conversation state machine logic."""

    def test_valid_transitions(self):
        """Test that valid transitions work correctly."""
        assert validate_transition(
            ConversationState.INITIALIZING, ConversationState.GENERATING_QUESTIONS
        )
        assert validate_transition(
            ConversationState.GENERATING_QUESTIONS, ConversationState.WAITING_FOR_INPUT
        )
        assert validate_transition(
            ConversationState.WAITING_FOR_INPUT, ConversationState.PROCESSING_ANSWER
        )
        assert validate_transition(
            ConversationState.PROCESSING_ANSWER, ConversationState.GENERATING_FOLLOWUPS
        )
        assert validate_transition(
            ConversationState.GENERATING_REQUIREMENTS, ConversationState.COMPLETED
        )

    def test_invalid_transitions(self):
        """Test that invalid transitions are rejected."""
        assert not validate_transition(
            ConversationState.COMPLETED, ConversationState.WAITING_FOR_INPUT
        )
        assert not validate_transition(
            ConversationState.FAILED, ConversationState.INITIALIZING
        )
        assert not validate_transition(
            ConversationState.INITIALIZING, ConversationState.PROCESSING_ANSWER
        )
        assert not validate_transition(
            ConversationState.WAITING_FOR_INPUT, ConversationState.GENERATING_QUESTIONS
        )
        assert not validate_transition(
            ConversationState.ASSESSING_COMPLETENESS, ConversationState.GENERATING_QUESTIONS
        )

    def test_terminal_states(self):
        """Test terminal state detection."""
        assert is_terminal_state(ConversationState.COMPLETED)
        assert is_terminal_state(ConversationState.FAILED)
        assert not is_terminal_state(ConversationState.WAITING_FOR_INPUT)
        assert not is_terminal_state(ConversationState.PROCESSING_ANSWER)

    def test_recovery_capability(self):
        """Test recovery capability detection."""
        assert can_recover_from_state(ConversationState.INITIALIZING)
        assert can_recover_from_state(ConversationState.WAITING_FOR_INPUT)
        assert can_recover_from_state(ConversationState.PROCESSING_ANSWER)
        assert not can_recover_from_state(ConversationState.COMPLETED)
        assert not can_recover_from_state(ConversationState.FAILED)


class TestStateContext:
    """Test state context serialization."""

    def test_default_context(self):
        """Test default state context creation."""
        context = StateContext()
        assert context.current_question_index == 0
        assert context.pending_followups == []
        assert context.analysis_in_progress is None
        assert context.llm_operation_id is None

    def test_context_serialization(self):
        """Test state context can be serialized and deserialized."""
        context = StateContext(
            current_question_index=5,
            pending_followups=["follow1", "follow2"],
            analysis_in_progress="analyzing response",
            llm_operation_id="op_123",
        )

        data = context.model_dump()
        restored = StateContext.model_validate(data)

        assert restored.current_question_index == 5
        assert restored.pending_followups == ["follow1", "follow2"]
        assert restored.analysis_in_progress == "analyzing response"
        assert restored.llm_operation_id == "op_123"
