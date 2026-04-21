from zheng_agent.agents.llm.base import BaseLLMAgent
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec


class ChatAgent(BaseLLMAgent):
    """A conversational agent that responds to user messages."""

    SYSTEM_PROMPT = """你是一个友好的对话助手。用户会发送消息给你，你需要回复。

你必须以 JSON 格式回复：
{"decision_type": "complete", "reasoning": "...", "final_result": {"response": "你的回复内容"}}

注意：
- 回复应该自然、友好
- 直接回复用户的问题或话题
- 不要提到 JSON 格式或决策类型
- response 字段包含你的实际回复文本"""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7, api_key: str | None = None):
        super().__init__(model, temperature)
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package not installed. Run: pip install zheng-agent[openai]") from e
        self.client = OpenAI(api_key=api_key)

    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def _build_prompt(self, task_spec: TaskSpec, run_context: RunContext) -> str:
        """Build chat prompt from user message."""
        user_message = run_context.task_input.get("message", "")
        return f"用户消息：{user_message}\n\n请回复："