from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec


class ScriptedMockAgent(AgentProtocol):
    def __init__(self, decisions: list[AgentDecision]):
        self._decisions = decisions
        self._index = 0

    def decide(self, task_spec: TaskSpec, run_context: RunContext) -> AgentDecision:
        decision = self._decisions[self._index]
        self._index += 1
        return decision