from dataclasses import dataclass

ALLOWED_RUN_TRANSITIONS = {
    "created": {
        "validate_passed": "validated",
        "validate_failed": "failed",
        "cancel_requested": "cancelled",
    },
    "validated": {
        "prepare_run": "ready",
        "cancel_requested": "cancelled",
    },
    "ready": {
        "start_run": "running",
        "cancel_requested": "cancelled",
    },
    "running": {
        "action_requested": "waiting_action",
        "pause_requested": "paused",
        "run_succeeded": "completed",
        "run_failed": "failed",
        "cancel_requested": "cancelled",
    },
    "waiting_action": {
        "action_completed": "running",
        "action_rejected": "failed",
        "action_failed": "failed",
        "cancel_requested": "cancelled",
    },
    "paused": {
        "resume_requested": "running",
        "cancel_requested": "cancelled",
    },
}

ALLOWED_STEP_TRANSITIONS = {
    "pending": {"step_scheduled": "ready"},
    "ready": {"step_started": "running", "step_error": "failed"},
    "running": {
        "decision_request_action": "waiting_action",
        "decision_respond": "completed",
        "decision_complete": "completed",
        "decision_fail": "failed",
        "step_error": "failed",
    },
    "waiting_action": {
        "action_completed": "running",
        "action_rejected": "failed",
        "action_failed": "failed",
        "step_error": "failed",
    },
}


@dataclass(slots=True)
class StateTransitionError(Exception):
    status: str
    event: str

    def __str__(self) -> str:
        return f"illegal transition: status={self.status}, event={self.event}"


def _apply_transition(table: dict[str, dict[str, str]], status: str, event: str) -> str:
    next_state = table.get(status, {}).get(event)
    if next_state is None:
        raise StateTransitionError(status=status, event=event)
    return next_state


def apply_run_event(status: str, event: str) -> str:
    return _apply_transition(ALLOWED_RUN_TRANSITIONS, status, event)


def apply_step_event(status: str, event: str) -> str:
    return _apply_transition(ALLOWED_STEP_TRANSITIONS, status, event)