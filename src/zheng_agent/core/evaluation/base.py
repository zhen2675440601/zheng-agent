from typing import Protocol

from zheng_agent.core.contracts import EvalResult, RunResult, TaskSpec
from zheng_agent.core.tracing.events import TraceEvent


class RunEvaluator(Protocol):
    def evaluate(
        self,
        task_spec: TaskSpec,
        trace: list[TraceEvent],
        final_result: RunResult,
    ) -> EvalResult:
        ...