from typing import Literal

from pydantic import BaseModel, Field

AgentType = Literal["mock", "openai"]
RuntimeMode = Literal["default", "chat", "task"]
CheckpointKind = Literal["pause", "action_before", "action_after", "step_boundary"]


class RecoveryError(Exception):
    """Raised when agent recovery fails due to missing or invalid metadata."""

    def __init__(self, agent_type: str, reason: str):
        self.agent_type = agent_type
        self.reason = reason
        super().__init__(f"Recovery failed for {agent_type}: {reason}")


class AgentRecoveryMetadata(BaseModel):
    """Agent-specific recovery data for checkpoint restoration.

    Required fields (all providers):
    - agent_type: identifies the provider

    Provider-specific fields in recovery_data:
    - mock: decisions (serialized list), current_index
    - openai: model, temperature, message_history, last_prompt_context
    """

    agent_type: AgentType
    recovery_data: dict = Field(default_factory=dict)

    def validate_for_restore(self) -> None:
        """Validate that recovery_data contains required fields for the agent type."""
        if self.agent_type == "mock":
            if "decisions" not in self.recovery_data:
                raise RecoveryError("mock", "missing serialized decisions")
            if "current_index" not in self.recovery_data:
                raise RecoveryError("mock", "missing current_index")
        elif self.agent_type == "openai":
            if "model" not in self.recovery_data:
                raise RecoveryError("openai", "missing model")