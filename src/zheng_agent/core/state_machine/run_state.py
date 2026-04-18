from typing import Literal

RunStatus = Literal[
    "created",
    "validated",
    "ready",
    "running",
    "waiting_action",
    "paused",
    "completed",
    "failed",
    "cancelled",
]

RunEvent = Literal[
    "validate_passed",
    "validate_failed",
    "prepare_run",
    "start_run",
    "action_requested",
    "action_completed",
    "action_rejected",
    "action_failed",
    "pause_requested",
    "resume_requested",
    "run_succeeded",
    "run_failed",
    "cancel_requested",
]