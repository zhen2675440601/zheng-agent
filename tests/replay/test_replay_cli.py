from pathlib import Path

from zheng_agent.core.replay.replayer import replay_trace, get_trace_events, reevaluate_trace
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.tracing.events import build_trace_event
from zheng_agent.core.tracing.store import JsonlTraceStore
from zheng_agent.core.contracts import TaskSpec


def test_replay_trace_returns_summary(tmp_path: Path):
    path = tmp_path / "run-1.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-1", step_id=None, event_type="run_created", payload={"task_type": "demo"}, sequence_number=1))
    store.append(build_trace_event(run_id="run-1", step_id="step-1", event_type="step_started", payload={}, sequence_number=2))
    store.append(build_trace_event(run_id="run-1", step_id=None, event_type="run_completed", payload={"status": "completed"}, sequence_number=3))

    summary = replay_trace(path)

    assert summary["run_id"] == "run-1"
    assert summary["event_count"] == 3
    assert summary["terminal_event"] == "run_completed"
    assert "step-1" in summary["step_ids"]


def test_get_trace_events_returns_all_events(tmp_path: Path):
    path = tmp_path / "run-2.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-2", step_id=None, event_type="run_created", payload={}, sequence_number=1))
    store.append(build_trace_event(run_id="run-2", step_id="step-1", event_type="step_started", payload={}, sequence_number=2))

    events = get_trace_events(path)

    assert len(events) == 2
    assert events[0].event_type == "run_created"
    assert events[1].step_id == "step-1"


def test_reevaluate_trace_with_task_spec(tmp_path: Path):
    path = tmp_path / "run-3.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-3", step_id=None, event_type="run_created", payload={}, sequence_number=1))
    store.append(build_trace_event(run_id="run-3", step_id=None, event_type="run_completed", payload={"output": {"message": "hello"}}, sequence_number=2))

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object", "required_keys": ["message"]},
        allowed_actions=["echo"],
    )

    evaluator = BasicRunEvaluator()
    result = reevaluate_trace(path, evaluator, spec, final_status="completed")

    assert result["run_id"] == "run-3"
    assert result["passed"] is True


def test_reevaluate_trace_detects_missing_output(tmp_path: Path):
    path = tmp_path / "run-4.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-4", step_id=None, event_type="run_created", payload={}, sequence_number=1))
    store.append(build_trace_event(run_id="run-4", step_id=None, event_type="run_completed", payload={"output": {}}, sequence_number=2))

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object", "required_keys": ["message"]},
        allowed_actions=["echo"],
    )

    evaluator = BasicRunEvaluator()
    result = reevaluate_trace(path, evaluator, spec, final_status="completed")

    assert result["passed"] is False
    assert any("message" in reason for reason in result["reasons"])


def test_get_original_eval_result_extracts_from_trace(tmp_path: Path):
    path = tmp_path / "run-5.jsonl"
    store = JsonlTraceStore(path)
    store.append(build_trace_event(run_id="run-5", step_id=None, event_type="run_created", payload={}, sequence_number=1))
    store.append(build_trace_event(run_id="run-5", step_id=None, event_type="evaluation_completed", payload={"passed": True, "score": 1.0, "reasons": [], "metrics": {"trace_events": 5}}, sequence_number=2))

    from zheng_agent.core.replay.replayer import get_original_eval_result
    original = get_original_eval_result(path)

    assert original is not None
    assert original["passed"] is True
    assert original["score"] == 1.0
    assert original["metrics"]["trace_events"] == 5


def test_compare_eval_results_detects_match(tmp_path: Path):
    from zheng_agent.core.replay.replayer import compare_eval_results

    original = {"passed": True, "score": 1.0, "reasons": [], "metrics": {"events": 10}}
    reevaluated = {"passed": True, "score": 1.0, "reasons": [], "metrics": {"events": 10}}

    comparison = compare_eval_results(original, reevaluated)

    assert comparison["passed_match"] is True
    assert comparison["score_match"] is True
    assert comparison["reasons_match"] is True


def test_compare_eval_results_detects_mismatch(tmp_path: Path):
    from zheng_agent.core.replay.replayer import compare_eval_results

    original = {"passed": True, "score": 1.0, "reasons": []}
    reevaluated = {"passed": False, "score": 0.0, "reasons": ["missing_output_keys"]}

    comparison = compare_eval_results(original, reevaluated)

    assert comparison["passed_match"] is False
    assert comparison["score_match"] is False
    assert comparison["reasons_match"] is False