"""Tests for multi-step execution model."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from zheng_agent.core.contracts import TaskSpec, AgentDecision
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.runtime.state_store import RunState, RunStateStore
from zheng_agent.core.tracing import read_trace_events


def test_engine_supports_multiple_steps(tmp_path: Path):
    """Engine can execute multiple steps in sequence."""
    spec = TaskSpec(
        task_type="multi_step_demo",
        title="Multi-Step Demo",
        description="Task with multiple steps",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step1"}),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step2"}),
            AgentDecision(decision_type="complete", final_result={"steps_completed": 2}),
        ]
    )

    outcome = engine.run(spec, {"message": "test"}, agent, run_id="multi-step-run")

    assert outcome.run_result.status == "completed"
    assert outcome.run_result.output["steps_completed"] == 2

    events = read_trace_events(tmp_path / "multi-step-run.jsonl")
    step_scheduled_events = [e for e in events if e.event_type == "step_scheduled"]
    step_completed_events = [e for e in events if e.event_type == "step_completed"]

    assert len(step_scheduled_events) == 2
    assert len(step_completed_events) == 2
    assert step_scheduled_events[0].payload["step_id"] == "step-1"
    assert step_scheduled_events[1].payload["step_id"] == "step-2"


def test_step_index_increments_correctly(tmp_path: Path):
    """Step index increments when advancing steps."""
    spec = TaskSpec(
        task_type="step_index_test",
        title="Step Index Test",
        description="Test step index tracking",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"step_count": 4}),
        ]
    )

    engine.run(spec, {}, agent, run_id="step-index-run")

    events = read_trace_events(tmp_path / "step-index-run.jsonl")
    step_events = [e for e in events if e.event_type == "step_started"]

    assert len(step_events) == 4
    assert step_events[0].payload["step_index"] == 0
    assert step_events[1].payload["step_index"] == 1
    assert step_events[2].payload["step_index"] == 2
    assert step_events[3].payload["step_index"] == 3


def test_resume_preserves_step_position(tmp_path: Path):
    """Resume continues from the correct step position."""
    spec = TaskSpec(
        task_type="resume_step_test",
        title="Resume Step Test",
        description="Test resume step position",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step1"}),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step2"}),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"done": True}),
        ]
    )

    engine.request_pause()
    outcome1 = engine.run(spec, {}, agent1, run_id="resume-step-run")
    assert outcome1.run_result.status == "paused"

    state = engine.get_state("resume-step-run")
    assert state is not None
    assert state.step_index == 0
    assert state.step_id == "step-1"

    agent2 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step1"}),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step2"}),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"done": True}),
        ]
    )

    outcome2 = engine.resume("resume-step-run", agent2)
    assert outcome2.run_result.status == "completed"

    events = read_trace_events(tmp_path / "resume-step-run.jsonl")
    step_scheduled_events = [e for e in events if e.event_type == "step_scheduled"]
    assert len(step_scheduled_events) >= 2

    run_resumed_events = [e for e in events if e.event_type == "run_resumed"]
    assert len(run_resumed_events) == 1
    assert "from_step" in run_resumed_events[0].payload


def test_respond_decision_continues_in_same_step(tmp_path: Path):
    """respond decision produces output without advancing step."""
    spec = TaskSpec(
        task_type="respond_test",
        title="Respond Test",
        description="Test respond decision",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="respond", response={"thinking": "analyzing..."}),
            AgentDecision(decision_type="respond", response={"thinking": "still thinking..."}),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "done"}),
            AgentDecision(decision_type="complete", final_result={"analysis": "complete"}),
        ]
    )

    outcome = engine.run(spec, {}, agent, run_id="respond-run")

    assert outcome.run_result.status == "completed"

    events = read_trace_events(tmp_path / "respond-run.jsonl")
    respond_events = [e for e in events if e.event_type == "agent_response"]
    step_completed_events = [e for e in events if e.event_type == "step_completed"]

    assert len(respond_events) == 2
    assert len(step_completed_events) == 1


def test_advance_step_with_no_prior_step_starts_first_step(tmp_path: Path):
    """advance_step at start creates first step then advances to second."""
    spec = TaskSpec(
        task_type="advance_first_test",
        title="Advance First Test",
        description="Test advance_step as first decision",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"skipped_first": True}),
        ]
    )

    engine.run(spec, {}, agent, run_id="advance-first-run")

    events = read_trace_events(tmp_path / "advance-first-run.jsonl")
    step_events = [e for e in events if e.event_type == "step_started"]

    assert len(step_events) >= 2


def test_step_lifecycle_events_are_emitted(tmp_path: Path):
    """Step lifecycle events are emitted correctly."""
    spec = TaskSpec(
        task_type="lifecycle_test",
        title="Lifecycle Test",
        description="Test step lifecycle events",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "hello"}),
            AgentDecision(decision_type="complete", final_result={"done": True}),
        ]
    )

    outcome = engine.run(spec, {}, agent, run_id="lifecycle-run")
    assert outcome.run_result.status == "completed"

    events = read_trace_events(tmp_path / "lifecycle-run.jsonl")
    for expected_type in ["step_scheduled", "step_started", "step_completed"]:
        matching = [e for e in events if e.event_type == expected_type]
        assert len(matching) >= 1


def test_run_completed_reports_total_steps(tmp_path: Path):
    """run_completed event includes total_steps count."""
    spec = TaskSpec(
        task_type="total_steps_test",
        title="Total Steps Test",
        description="Test total steps reporting",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"steps": 3}),
        ]
    )

    engine.run(spec, {}, agent, run_id="total-steps-run")

    events = read_trace_events(tmp_path / "total-steps-run.jsonl")
    completed_events = [e for e in events if e.event_type == "run_completed"]

    assert len(completed_events) == 1
    assert "total_steps" in completed_events[0].payload
    assert completed_events[0].payload["total_steps"] >= 3


def test_engine_fails_when_max_steps_exceeded(tmp_path: Path):
    """Run fails when it tries to start a step beyond max_steps."""
    spec = TaskSpec(
        task_type="max_steps_test",
        title="Max Steps Test",
        description="Test max steps guardrail",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
        max_steps=2,
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="advance_step"),
            AgentDecision(decision_type="complete", final_result={"done": True}),
        ]
    )

    outcome = engine.run(spec, {}, agent, run_id="max-steps-run")

    assert outcome.run_result.status == "failed"
    assert outcome.run_result.error == "run exceeded max_steps=2"
    assert outcome.eval_result.passed is False

    events = read_trace_events(tmp_path / "max-steps-run.jsonl")
    failed_events = [e for e in events if e.event_type == "run_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["error"] == "run exceeded max_steps=2"


def test_engine_fails_when_timeout_exceeded(tmp_path: Path):
    """Run fails immediately when resumed timeout budget is already exhausted."""
    spec = TaskSpec(
        task_type="timeout_test",
        title="Timeout Test",
        description="Test timeout guardrail",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
        timeout_seconds=1,
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    state = RunState(
        run_id="timeout-run",
        run_status="paused",
        step_id="step-1",
        step_status="running",
        step_index=0,
        sequence=3,
        started_at=(datetime.now(UTC) - timedelta(seconds=5)).isoformat(),
        task_spec=spec,
        task_input={},
        agent_recovery=ScriptedMockAgent(
            decisions=[AgentDecision(decision_type="complete", final_result={"done": True})]
        ).get_recovery_metadata(),
        checkpoint_kind="pause",
        checkpoint_reason="user_requested",
    )
    RunStateStore(tmp_path).save(state)

    agent = ScriptedMockAgent(
        decisions=[AgentDecision(decision_type="complete", final_result={"done": True})]
    )

    outcome = engine.resume("timeout-run", agent)

    assert outcome.run_result.status == "failed"
    assert outcome.run_result.error == "run exceeded timeout_seconds=1"
    assert outcome.eval_result.passed is False

    events = read_trace_events(tmp_path / "timeout-run.jsonl")
    failed_events = [e for e in events if e.event_type == "run_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["error"] == "run exceeded timeout_seconds=1"
