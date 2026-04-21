from pathlib import Path

from zheng_agent.core.evaluation.base import RunEvaluator
from zheng_agent.core.tracing.reader import read_trace_events
from zheng_agent.core.tracing.events import TraceEvent


def replay_trace(path: Path) -> dict:
    """Get a summary of a trace file."""
    events = read_trace_events(path)
    if not events:
        return {
            "run_id": None,
            "event_count": 0,
            "terminal_event": None,
            "step_ids": [],
            "events": [],
        }

    return {
        "run_id": events[0].run_id,
        "event_count": len(events),
        "terminal_event": events[-1].event_type,
        "step_ids": list(set(event.step_id for event in events if event.step_id is not None)),
        "events": [event.model_dump(mode="json") for event in events],
    }


def get_trace_events(path: Path) -> list[TraceEvent]:
    """Read all events from a trace file."""
    return read_trace_events(path)


def reevaluate_trace(
    path: Path,
    evaluator: RunEvaluator,
    task_spec,
    final_status: str = "completed",
    final_output: dict | None = None,
) -> dict:
    """Re-run evaluation on a historical trace.

    Args:
        path: Path to the trace file
        evaluator: The evaluator to use
        task_spec: The original task spec
        final_status: The final run status (for RunResult)
        final_output: The final output (for RunResult)

    Returns:
        Evaluation result summary
    """
    from zheng_agent.core.contracts import RunResult

    events = read_trace_events(path)
    if not events:
        return {"error": "No events in trace"}

    run_id = events[0].run_id

    # Find final result from trace if not provided
    if final_output is None:
        for event in reversed(events):
            if event.event_type == "run_completed":
                final_output = event.payload.get("output", {})
                break

    run_result = RunResult(
        run_id=run_id,
        task_type=task_spec.task_type,
        status=final_status,
        output=final_output,
    )

    eval_result = evaluator.evaluate(task_spec, events, run_result)

    return {
        "run_id": run_id,
        "passed": eval_result.passed,
        "score": eval_result.score,
        "reasons": eval_result.reasons,
        "metrics": eval_result.metrics,
    }