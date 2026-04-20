from zheng_agent.core.contracts import EvalResult, RunResult, TaskSpec, validate_output
from zheng_agent.core.tracing.events import TraceEvent


class BasicRunEvaluator:
    def evaluate(
        self,
        task_spec: TaskSpec,
        trace: list[TraceEvent],
        final_result: RunResult,
    ) -> EvalResult:
        output_valid, output_errors = validate_output(task_spec.output_schema, final_result.output)
        rejected_actions = [event for event in trace if event.event_type == "action_rejected"]

        reasons: list[str] = []
        if not output_valid:
            reasons.extend(output_errors)
        if rejected_actions:
            reasons.append("rejected_action_present")

        return EvalResult(
            passed=not reasons,
            score=1.0 if not reasons else 0.0,
            reasons=reasons,
            metrics={"trace_events": len(trace)},
        )