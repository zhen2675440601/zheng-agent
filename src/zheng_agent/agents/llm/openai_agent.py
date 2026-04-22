from zheng_agent.agents.llm.base import BaseLLMAgent
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec


class OpenAIAgent(BaseLLMAgent):
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.0, api_key: str | None = None):
        super().__init__(model, temperature)
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client for testability."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise ImportError("openai package not installed. Run: pip install zheng-agent[openai]") from e
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def _call_llm(self, prompt: str) -> str:
        """Call OpenAI API through client boundary."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a task execution agent. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def set_client_for_testing(self, mock_client) -> None:
        """Inject a mock client for testing without network dependency."""
        self._client = mock_client