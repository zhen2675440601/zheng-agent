from pathlib import Path

from zheng_agent.core.replay.replayer import replay_trace
from zheng_agent.core.tracing.events import build_trace_event
from zheng_agent.core.tracing.store import JsonlTraceStore


def test_replay_trace_returns_semantic_summary(tmp_path: Path):
    path = tmp_path / "run-1.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-1", step_id=None, event_type="run_created", payload={}, sequence_number=1))
    store.append(build_trace_event(run_id="run-1", step_id="step-1", event_type="step_started", payload={}, sequence_number=2))
    store.append(build_trace_event(run_id="run-1", step_id=None, event_type="run_completed", payload={}, sequence_number=3))

    summary = replay_trace(path)

    assert summary["run_id"] == "run-1"
    assert summary["event_count"] == 3
    assert summary["terminal_event"] == "run_completed"