from pathlib import Path

from zheng_agent.core.tracing.events import build_trace_event
from zheng_agent.core.tracing.reader import read_trace_events
from zheng_agent.core.tracing.store import JsonlTraceStore


def test_jsonl_store_appends_and_reads_in_order(tmp_path: Path):
    trace_path = tmp_path / "run-1.jsonl"
    store = JsonlTraceStore(trace_path)

    store.append(
        build_trace_event(
            run_id="run-1",
            step_id=None,
            event_type="run_created",
            payload={"task_type": "demo"},
            sequence_number=1,
        )
    )
    store.append(
        build_trace_event(
            run_id="run-1",
            step_id="step-1",
            event_type="step_started",
            payload={"attempt_id": "attempt-1"},
            sequence_number=2,
        )
    )

    events = read_trace_events(trace_path)

    assert [event.sequence_number for event in events] == [1, 2]
    assert events[1].step_id == "step-1"