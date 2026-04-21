from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ActionStatus = Literal["success", "failed", "rejected"]
ErrorCategory = Literal["validation_error", "not_allowed", "adapter_error", "timeout", "unknown"]


class ActionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    step_id: str
    action_name: str
    action_input: dict
    requested_by: str
    caused_by_decision_id: str | None = None
    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionResult(BaseModel):
    request_id: str | None = None
    status: ActionStatus
    output: dict | None = None
    error: str | None = None
    error_category: ErrorCategory | None = None
    result_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = Field(default_factory=dict)