"""Enhanced replay module for structured trace reconstruction and verification."""

from pathlib import Path
from dataclasses import dataclass
from typing import Literal

from zheng_agent.core.evaluation.base import RunEvaluator
from zheng_agent.core.tracing.reader import read_trace_events
from zheng_agent.core.tracing.events import TraceEvent, EVENT_PAYLOAD_TYPES


ReplayVersion = Literal["1.0"]


@dataclass
class ReplayProvenance:
    """Provenance information for replay reconstruction."""
    trace_version: ReplayVersion = "1.0"
    evaluator_type: str = "BasicRunEvaluator"
    reconstructed_from: str = "run_completed_event"
    trace_path: str = ""
    event_count: int = 0


@dataclass
class ReconstructedRun:
    """Reconstructed run state from trace analysis."""
    run_id: str
    run_status: str
    final_output: dict | None
    total_steps: int
    step_sequence: list[str]
    action_count: int
    has_failures: bool
    failure_reason: str | None


def replay_trace(path: Path) -> dict:
    """Get a summary of a trace file with preserved step ordering."""
    events = read_trace_events(path)
    if not events:
        return {
            "run_id": None,
            "event_count": 0,
            "terminal_event": None,
            "step_ids": [],
            "step_sequence": [],
            "events": [],
            "provenance": None,
        }

    # Preserve step ordering by tracking first occurrence
    step_sequence: list[str] = []
    for event in events:
        if event.step_id and event.step_id not in step_sequence:
            step_sequence.append(event.step_id)

    provenance = ReplayProvenance(
        trace_version="1.0",
        trace_path=str(path),
        event_count=len(events),
    )

    return {
        "run_id": events[0].run_id,
        "event_count": len(events),
        "terminal_event": events[-1].event_type,
        "step_ids": step_sequence,  # Ordered list, not set
        "step_sequence": step_sequence,
        "events": [event.model_dump(mode="json") for event in events],
        "provenance": provenance.__dict__,
    }


def reconstruct_run_from_trace(path: Path) -> ReconstructedRun | None:
    """Reconstruct run state from trace using typed payloads."""
    events = read_trace_events(path)
    if not events:
        return None

    run_id = events[0].run_id
    run_status = "unknown"
    final_output = None
    total_steps = 0
    step_sequence: list[str] = []
    action_count = 0
    has_failures = False
    failure_reason = None

    for event in events:
        # Use typed payload extraction for core events
        typed_payload = event.get_typed_payload()

        if event.event_type == "step_started" and typed_payload:
            step_id = typed_payload.step_id if hasattr(typed_payload, 'step_id') else event.step_id
            if step_id and step_id not in step_sequence:
                step_sequence.append(step_id)

        if event.event_type == "action_executed":
            action_count += 1

        if event.event_type == "run_completed" and typed_payload:
            run_status = typed_payload.status if hasattr(typed_payload, 'status') else "completed"
            final_output = typed_payload.output if hasattr(typed_payload, 'output') else None
            if hasattr(typed_payload, 'total_steps'):
                total_steps = typed_payload.total_steps

        if event.event_type == "run_failed" and typed_payload:
            run_status = "failed"
            has_failures = True
            failure_reason = typed_payload.error if hasattr(typed_payload, 'error') else None

        if event.event_type == "step_failed":
            has_failures = True

    total_steps = max(total_steps, len(step_sequence))

    return ReconstructedRun(
        run_id=run_id,
        run_status=run_status,
        final_output=final_output,
        total_steps=total_steps,
        step_sequence=step_sequence,
        action_count=action_count,
        has_failures=has_failures,
        failure_reason=failure_reason,
    )


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
    """Re-run evaluation on a historical trace with provenance tracking."""
    from zheng_agent.core.contracts import RunResult

    events = read_trace_events(path)
    if not events:
        return {
            "error": "No events in trace",
            "provenance": None,
        }

    run_id = events[0].run_id

    # Reconstruct from typed event if possible
    if final_output is None:
        for event in reversed(events):
            if event.event_type == "run_completed":
                typed_payload = event.get_typed_payload()
                if typed_payload and hasattr(typed_payload, 'output'):
                    final_output = typed_payload.output
                    final_status = typed_payload.status if hasattr(typed_payload, 'status') else "completed"
                else:
                    final_output = event.payload.get("output", {})
                break

    run_result = RunResult(
        run_id=run_id,
        task_type=task_spec.task_type,
        status=final_status,
        output=final_output,
    )

    eval_result = evaluator.evaluate(task_spec, events, run_result)

    provenance = ReplayProvenance(
        trace_version="1.0",
        evaluator_type=evaluator.__class__.__name__,
        reconstructed_from="run_completed_event",
        trace_path=str(path),
        event_count=len(events),
    )

    return {
        "run_id": run_id,
        "passed": eval_result.passed,
        "score": eval_result.score,
        "reasons": eval_result.reasons,
        "metrics": eval_result.metrics,
        "provenance": provenance.__dict__,
    }


def get_original_eval_result(path: Path) -> dict | None:
    """Extract the original evaluation result with provenance."""
    events = read_trace_events(path)
    for event in events:
        if event.event_type == "evaluation_completed":
            typed_payload = event.get_typed_payload()
            if typed_payload:
                return {
                    "passed": typed_payload.passed,
                    "score": typed_payload.score,
                    "reasons": typed_payload.reasons,
                    "metrics": typed_payload.metrics,
                    "provenance": {
                        "source": "evaluation_completed_event",
                        "sequence_number": event.sequence_number,
                    },
                }
            return {
                "passed": event.payload.get("passed"),
                "score": event.payload.get("score"),
                "reasons": event.payload.get("reasons", []),
                "metrics": event.payload.get("metrics", {}),
                "provenance": {
                    "source": "evaluation_completed_event",
                    "sequence_number": event.sequence_number,
                },
            }
    return None


def compare_eval_results(original: dict, reevaluated: dict) -> dict:
    """Compare original and re-evaluated results with reconstruction evidence."""
    passed_match = original.get("passed") == reevaluated.get("passed")
    score_match = original.get("score") == reevaluated.get("score")
    reasons_match = original.get("reasons") == reevaluated.get("reasons")

    # Include provenance comparison
    original_prov = original.get("provenance", {})
    reeval_prov = reevaluated.get("provenance", {})

    return {
        "passed_match": passed_match,
        "score_match": score_match,
        "reasons_match": reasons_match,
        "full_match": passed_match and score_match and reasons_match,
        "original": original,
        "reevaluated": reevaluated,
        "provenance_comparison": {
            "original_source": original_prov.get("source", "unknown"),
            "reevaluated_source": reeval_prov.get("reconstructed_from", "unknown"),
            "evaluator_type": reeval_prov.get("evaluator_type", "unknown"),
            "trace_version": reeval_prov.get("trace_version", "unknown"),
        },
    }


def validate_trace_events(path: Path) -> dict:
    """Validate trace events against typed payload schemas."""
    events = read_trace_events(path)
    validation_results = {
        "valid": True,
        "errors": [],
        "validated_count": 0,
        "typed_count": 0,
    }

    for event in events:
        if event.event_type in EVENT_PAYLOAD_TYPES:
            typed_payload = event.get_typed_payload()
            if typed_payload is None:
                validation_results["errors"].append({
                    "sequence_number": event.sequence_number,
                    "event_type": event.event_type,
                    "error": "payload validation failed",
                })
                validation_results["valid"] = False
            else:
                validation_results["typed_count"] += 1
        validation_results["validated_count"] += 1

    return validation_results