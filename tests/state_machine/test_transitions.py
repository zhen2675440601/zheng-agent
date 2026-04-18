import pytest

from zheng_agent.core.state_machine.transitions import (
    StateTransitionError,
    apply_run_event,
    apply_step_event,
)


def test_run_transition_created_to_validated():
    assert apply_run_event("created", "validate_passed") == "validated"


def test_run_transition_rejects_illegal_shortcut():
    with pytest.raises(StateTransitionError):
        apply_run_event("created", "start_run")


def test_step_transition_waiting_action_returns_to_running():
    assert apply_step_event("waiting_action", "action_completed") == "running"


def test_step_transition_rejects_repeated_start():
    with pytest.raises(StateTransitionError):
        apply_step_event("running", "step_started")