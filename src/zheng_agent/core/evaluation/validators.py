from zheng_agent.core.contracts import EvalResult, RunResult, TaskSpec, validate_output
from zheng_agent.core.tracing.events import TraceEvent, EVENT_PAYLOAD_TYPES


class BasicRunEvaluator:
    def evaluate(
        self,
        task_spec: TaskSpec,
        trace: list[TraceEvent],
        final_result: RunResult,
    ) -> EvalResult:
        output_valid, output_errors = validate_output(task_spec.output_schema, final_result.output)
        rejected_actions = [event for event in trace if event.event_type == "action_rejected"]
        failed_actions = [event for event in trace if event.event_type == "action_failed"]
        step_failures = [event for event in trace if event.event_type == "step_failed"]
        run_failures = [event for event in trace if event.event_type == "run_failed"]

        # Count typed payload validation failures
        payload_validation_failures = 0
        for event in trace:
            if event.event_type in EVENT_PAYLOAD_TYPES:
                if event.get_typed_payload() is None:
                    payload_validation_failures += 1

        # Count checkpoint and recovery events
        checkpoint_events = [event for event in trace if event.event_type in ("run_paused", "run_resumed")]

        reasons: list[str] = []
        if final_result.status != "completed":
            reasons.append(f"run_status_{final_result.status}")
        if not output_valid:
            reasons.extend(output_errors)
        if rejected_actions:
            reasons.append("rejected_action_present")
        if failed_actions:
            reasons.append(f"action_failed_count_{len(failed_actions)}")
        if step_failures:
            reasons.append(f"step_failed_count_{len(step_failures)}")
        if payload_validation_failures > 0:
            reasons.append(f"payload_validation_failures_{payload_validation_failures}")

        metrics = {
            "trace_events": len(trace),
            "typed_payload_count": sum(1 for e in trace if e.event_type in EVENT_PAYLOAD_TYPES),
            "payload_validation_failures": payload_validation_failures,
            "checkpoint_events": len(checkpoint_events),
            "step_count": len([e for e in trace if e.event_type == "step_started"]),
            "action_count": len([e for e in trace if e.event_type == "action_executed"]),
        }

        return EvalResult(
            passed=not reasons,
            score=1.0 if not reasons else 0.0,
            reasons=reasons,
            metrics=metrics,
        )
