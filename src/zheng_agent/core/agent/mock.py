from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata


class ScriptedMockAgent(AgentProtocol):
    def __init__(self, decisions: list[AgentDecision]):
        self._decisions = decisions
        self._index = 0

    def decide(self, task_spec: TaskSpec, run_context: RunContext) -> AgentDecision:
        if self._index >= len(self._decisions):
            return AgentDecision(decision_type="fail", failure_reason="no_more_decisions")
        decision = self._decisions[self._index]
        self._index += 1
        return decision

    def get_recovery_metadata(self) -> AgentRecoveryMetadata:
        return AgentRecoveryMetadata(
            agent_type="mock",
            recovery_data={"decisions_count": len(self._decisions), "current_index": self._index},
        )

    def restore_from_metadata(self, metadata: AgentRecoveryMetadata) -> None:
        if metadata.agent_type == "mock":
            self._index = metadata.recovery_data.get("current_index", 0)