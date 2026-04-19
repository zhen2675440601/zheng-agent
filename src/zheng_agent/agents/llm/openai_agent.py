from zheng_agent.agents.llm.base import BaseLLMAgent
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec


class OpenAIAgent(BaseLLMAgent):
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0, api_key: str | None = None):
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
                {"role": "system", "content": "You are a task execution agent. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""