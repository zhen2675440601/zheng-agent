from zheng_agent.core.contracts import EvalResult, RunResult, TaskSpec
from zheng_agent.core.tracing.events import TraceEvent


class BasicRunEvaluator:
    def evaluate(
        self,
        task_spec: TaskSpec,
        trace: list[TraceEvent],
        final_result: RunResult,
    ) -> EvalResult:
        required_keys = task_spec.output_schema.get("required_keys", [])
        output = final_result.output or {}
        missing_keys = [key for key in required_keys if key not in output]
        rejected_actions = [event for event in trace if event.event_type == "action_rejected"]

        reasons: list[str] = []
        if missing_keys:
            reasons.append("missing_output_keys")
        if rejected_actions:
            reasons.append("rejected_action_present")

        return EvalResult(
            passed=not reasons,
            score=1.0 if not reasons else 0.0,
            reasons=reasons,
            metrics={"trace_events": len(trace)},
        )