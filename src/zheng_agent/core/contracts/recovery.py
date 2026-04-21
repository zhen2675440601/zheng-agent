from typing import Literal

from pydantic import BaseModel, Field

AgentType = Literal["mock", "openai"]
RuntimeMode = Literal["default", "chat", "task"]
CheckpointKind = Literal["pause", "action_before", "action_after", "step_boundary"]


class AgentRecoveryMetadata(BaseModel):
    """Agent-specific recovery data for checkpoint restoration."""

    agent_type: AgentType
    recovery_data: dict = Field(default_factory=dict)