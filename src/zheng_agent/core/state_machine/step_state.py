from typing import Literal

StepStatus = Literal[
    "pending",
    "ready",
    "running",
    "waiting_action",
    "completed",
    "failed",
]

StepEvent = Literal[
    "step_scheduled",
    "step_started",
    "decision_request_action",
    "decision_respond",
    "decision_complete",
    "decision_fail",
    "action_completed",
    "action_rejected",
    "action_failed",
    "step_error",
]