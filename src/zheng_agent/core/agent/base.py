from typing import Protocol

from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec


class AgentProtocol(Protocol):
    def decide(self, task_spec: TaskSpec, run_context: RunContext) -> AgentDecision:
        ...