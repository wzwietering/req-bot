import logging

from requirements_bot.core.conversation_state import (
    ConversationState,
    VALID_TRANSITIONS,
    validate_state_machine_completeness,
)
from requirements_bot.core.logging import log_event


def validate_state_machine_on_startup() -> bool:
    """Validate state machine configuration on application startup."""
    issues = validate_state_machine_completeness()

    if issues:
        for issue in issues:
            log_event(
                "state_machine.validation_failed",
                component="state_validation",
                operation="startup_validation",
                issue=issue,
                level=logging.ERROR,
            )
        return False

    log_event(
        "state_machine.validation_passed",
        component="state_validation",
        operation="startup_validation",
        total_states=len(ConversationState),
        total_transitions=sum(
            len(transitions) for transitions in VALID_TRANSITIONS.values()
        ),
        level=logging.INFO,
    )
    return True


def get_state_machine_stats() -> dict:
    """Get statistics about the state machine configuration."""
    all_states = set(ConversationState)
    terminal_states = {ConversationState.COMPLETED, ConversationState.FAILED}
    non_terminal_states = all_states - terminal_states

    total_transitions = sum(
        len(transitions) for transitions in VALID_TRANSITIONS.values()
    )

    # Calculate state connectivity
    reachable = {ConversationState.INITIALIZING}
    for state, transitions in VALID_TRANSITIONS.items():
        reachable.update(transitions)

    return {
        "total_states": len(all_states),
        "terminal_states": len(terminal_states),
        "non_terminal_states": len(non_terminal_states),
        "total_transitions": total_transitions,
        "reachable_states": len(reachable),
        "unreachable_states": len(all_states - reachable),
        "average_transitions_per_state": (
            total_transitions / len(VALID_TRANSITIONS) if VALID_TRANSITIONS else 0
        ),
    }


def diagnose_state_machine() -> dict:
    """Perform comprehensive state machine diagnostics."""
    issues = validate_state_machine_completeness()
    stats = get_state_machine_stats()

    # Check for potential issues
    warnings = []

    if stats["unreachable_states"] > 0:
        warnings.append("Some states are unreachable from the initial state")

    if stats["average_transitions_per_state"] < 1.5:
        warnings.append("State machine may be too linear (low transition density)")

    if stats["average_transitions_per_state"] > 4.0:
        warnings.append("State machine may be overly complex (high transition density)")

    return {
        "validation_passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "statistics": stats,
    }
