from typing import Literal

from pydantic import BaseModel, model_validator

DecisionType = Literal["request_action", "respond", "complete", "fail"]


class AgentDecision(BaseModel):
    decision_type: DecisionType
    reasoning: str | None = None
    action_name: str | None = None
    action_input: dict | None = None
    response: dict | None = None
    final_result: dict | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.decision_type == "request_action" and (
            self.action_name is None or self.action_input is None
        ):
            raise ValueError("request_action requires action_name and action_input")
        if self.decision_type == "complete" and self.final_result is None:
            raise ValueError("complete requires final_result")
        if self.decision_type == "fail" and self.failure_reason is None:
            raise ValueError("fail requires failure_reason")
        return self