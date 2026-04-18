from typing import Literal

from pydantic import BaseModel, Field

ActionStatus = Literal["success", "failed", "rejected"]


class ActionRequest(BaseModel):
    run_id: str
    step_id: str
    action_name: str
    action_input: dict
    requested_by: str


class ActionResult(BaseModel):
    status: ActionStatus
    output: dict | None = None
    error: str | None = None
    metadata: dict = Field(default_factory=dict)