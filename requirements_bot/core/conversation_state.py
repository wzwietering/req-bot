from datetime import UTC, datetime
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel


class ConversationState(Enum):
    """All possible conversation states in the interview pipeline."""

    INITIALIZING = "initializing"
    GENERATING_QUESTIONS = "generating_questions"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING_ANSWER = "processing_answer"
    GENERATING_FOLLOWUPS = "generating_followups"
    ASSESSING_COMPLETENESS = "assessing_completeness"
    GENERATING_REQUIREMENTS = "generating_requirements"
    COMPLETED = "completed"
    FAILED = "failed"


class StateContext(BaseModel):
    """Context needed to recover from interruptions."""

    current_question_index: int = 0
    pending_followups: List[str] = []
    analysis_in_progress: Optional[str] = None
    llm_operation_id: Optional[str] = None


# Valid state transitions - keeps the state machine simple and predictable
VALID_TRANSITIONS: Dict[ConversationState, Set[ConversationState]] = {
    ConversationState.INITIALIZING: {
        ConversationState.GENERATING_QUESTIONS,
        ConversationState.FAILED,
    },
    ConversationState.GENERATING_QUESTIONS: {
        ConversationState.WAITING_FOR_INPUT,
        ConversationState.FAILED,
    },
    ConversationState.WAITING_FOR_INPUT: {
        ConversationState.PROCESSING_ANSWER,
        ConversationState.GENERATING_REQUIREMENTS,
        ConversationState.COMPLETED,
        ConversationState.FAILED,
    },
    ConversationState.PROCESSING_ANSWER: {
        ConversationState.GENERATING_FOLLOWUPS,
        ConversationState.ASSESSING_COMPLETENESS,
        ConversationState.WAITING_FOR_INPUT,
        ConversationState.FAILED,
    },
    ConversationState.GENERATING_FOLLOWUPS: {
        ConversationState.WAITING_FOR_INPUT,
        ConversationState.ASSESSING_COMPLETENESS,
        ConversationState.FAILED,
    },
    ConversationState.ASSESSING_COMPLETENESS: {
        ConversationState.WAITING_FOR_INPUT,
        ConversationState.GENERATING_REQUIREMENTS,
        ConversationState.COMPLETED,
        ConversationState.FAILED,
    },
    ConversationState.GENERATING_REQUIREMENTS: {
        ConversationState.COMPLETED,
        ConversationState.FAILED,
    },
    ConversationState.COMPLETED: set(),  # Terminal state
    ConversationState.FAILED: set(),  # Terminal state
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


def validate_transition(
    from_state: ConversationState, to_state: ConversationState
) -> bool:
    """Check if a state transition is valid."""
    if not isinstance(from_state, ConversationState):
        raise ValueError(f"Invalid from_state type: {type(from_state)}")
    if not isinstance(to_state, ConversationState):
        raise ValueError(f"Invalid to_state type: {type(to_state)}")

    return to_state in VALID_TRANSITIONS.get(from_state, set())


def is_terminal_state(state: ConversationState) -> bool:
    """Check if state is terminal (no further transitions possible)."""
    if not isinstance(state, ConversationState):
        raise ValueError(f"Invalid state type: {type(state)}")

    return state in {ConversationState.COMPLETED, ConversationState.FAILED}


def can_recover_from_state(state: ConversationState) -> bool:
    """Check if we can recover from this state after interruption."""
    if not isinstance(state, ConversationState):
        raise ValueError(f"Invalid state type: {type(state)}")

    # Terminal states cannot be recovered from
    if is_terminal_state(state):
        return False

    # Explicitly list recoverable states for clarity
    recoverable_states = {
        ConversationState.INITIALIZING,
        ConversationState.GENERATING_QUESTIONS,
        ConversationState.WAITING_FOR_INPUT,
        ConversationState.PROCESSING_ANSWER,
        ConversationState.GENERATING_FOLLOWUPS,
        ConversationState.ASSESSING_COMPLETENESS,
        ConversationState.GENERATING_REQUIREMENTS,
    }

    return state in recoverable_states


def validate_context_for_state(
    state: ConversationState, context: StateContext
) -> list[str]:
    """Validate that context is appropriate for the given state."""
    if not isinstance(state, ConversationState):
        raise ValueError(f"Invalid state type: {type(state)}")
    if not isinstance(context, StateContext):
        raise ValueError(f"Invalid context type: {type(context)}")

    validators = {
        ConversationState.WAITING_FOR_INPUT: _validate_waiting_context,
        ConversationState.PROCESSING_ANSWER: _validate_processing_context,
        ConversationState.GENERATING_FOLLOWUPS: _validate_followups_context,
        ConversationState.GENERATING_QUESTIONS: _validate_questions_generation_context,
        ConversationState.GENERATING_REQUIREMENTS: _validate_requirements_generation_context,
    }

    validator = validators.get(state, lambda ctx: [])
    return validator(context)


def _validate_waiting_context(context: StateContext) -> list[str]:
    """Validate context for WAITING_FOR_INPUT state."""
    issues = []
    if context.current_question_index < 0:
        issues.append("Current question index cannot be negative")
    return issues


def _validate_processing_context(context: StateContext) -> list[str]:
    """Validate context for PROCESSING_ANSWER state."""
    issues = []
    if context.current_question_index < 0:
        issues.append("Current question index cannot be negative for answer processing")
    return issues


def _validate_followups_context(context: StateContext) -> list[str]:
    """Validate context for GENERATING_FOLLOWUPS state."""
    issues = []
    if not context.analysis_in_progress:
        issues.append("Analysis in progress should be set when generating follow-ups")
    return issues


def _validate_questions_generation_context(context: StateContext) -> list[str]:
    """Validate context for GENERATING_QUESTIONS state."""
    issues = []
    if context.llm_operation_id and not context.llm_operation_id.startswith(
        ("generate_", "retry_")
    ):
        issues.append("LLM operation ID should indicate question generation operation")
    return issues


def _validate_requirements_generation_context(context: StateContext) -> list[str]:
    """Validate context for GENERATING_REQUIREMENTS state."""
    issues = []
    if context.llm_operation_id and not context.llm_operation_id.startswith(
        ("generate_", "retry_")
    ):
        issues.append(
            "LLM operation ID should indicate requirements generation operation"
        )
    return issues


def validate_state_machine_completeness() -> list[str]:
    """Validate that all states have defined transitions and catch orphaned states."""
    issues = []
    all_states = set(ConversationState)
    defined_states = set(VALID_TRANSITIONS.keys())

    # Check for states without transitions defined
    orphaned_states = all_states - defined_states
    if orphaned_states:
        issues.append(f"States without transitions: {orphaned_states}")

    # Check for unreachable states
    reachable = {ConversationState.INITIALIZING}
    for state, transitions in VALID_TRANSITIONS.items():
        reachable.update(transitions)

    unreachable = all_states - reachable
    if unreachable:
        issues.append(f"Unreachable states: {unreachable}")

    return issues
