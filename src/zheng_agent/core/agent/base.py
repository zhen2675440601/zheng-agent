from typing import Protocol

from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata


class AgentProtocol(Protocol):
    def decide(self, task_spec: TaskSpec, run_context: RunContext) -> AgentDecision:
        ...

    def get_recovery_metadata(self) -> AgentRecoveryMetadata:
        """Return agent-specific data needed for checkpoint restoration."""
        ...

    def restore_from_metadata(self, metadata: AgentRecoveryMetadata) -> None:
        """Restore agent state from checkpoint metadata."""
        ...