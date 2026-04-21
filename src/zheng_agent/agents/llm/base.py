from abc import ABC, abstractmethod

from zheng_agent.core.agent.base import AgentProtocol
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata


class BaseLLMAgent(AgentProtocol, ABC):
    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self._message_history: list[dict] = []

    def decide(self, task_spec: TaskSpec, run_context: RunContext) -> AgentDecision:
        prompt = self._build_prompt(task_spec, run_context)
        raw_response = self._call_llm(prompt)
        self._message_history.append({"role": "assistant", "content": raw_response})
        return self._parse_response(raw_response, task_spec)

    @abstractmethod
    def _call_llm(self, prompt: str) -> str:
        """调用具体 LLM API"""
        pass

    def _build_prompt(self, task_spec: TaskSpec, run_context: RunContext) -> str:
        """构造 prompt"""
        from zheng_agent.agents.llm.prompts import build_decision_prompt
        return build_decision_prompt(task_spec, run_context)

    def _parse_response(self, raw_response: str, task_spec: TaskSpec) -> AgentDecision:
        """解析 LLM 响应为 AgentDecision"""
        from zheng_agent.agents.llm.parser import parse_decision
        return parse_decision(raw_response, task_spec.allowed_actions)

    def get_recovery_metadata(self) -> AgentRecoveryMetadata:
        return AgentRecoveryMetadata(
            agent_type="openai",
            recovery_data={
                "model": self.model,
                "temperature": self.temperature,
                "message_history": self._message_history,
            },
        )

    def restore_from_metadata(self, metadata: AgentRecoveryMetadata) -> None:
        if metadata.agent_type == "openai":
            self._message_history = metadata.recovery_data.get("message_history", [])