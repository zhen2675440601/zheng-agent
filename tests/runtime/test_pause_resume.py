from pathlib import Path

from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision, TaskSpec
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunStateStore
from zheng_agent.core.tracing.reader import read_trace_events


def test_engine_can_pause_mid_execution(tmp_path: Path):
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"message": payload["message"]})
    gateway = ActionGatewayExecutor(registry)
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "first"},
            ),
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "second"},
            ),
            AgentDecision(
                decision_type="complete",
                final_result={"message": "done"},
            ),
        ]
    )
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    # Start run and request pause after first action
    engine.request_pause()
    outcome = engine.run(task_spec=spec, task_input={}, agent=agent)

    assert outcome.run_result.status == "paused"
    assert "run_paused" in [e.event_type for e in read_trace_events(tmp_path / f"{outcome.run_id}.jsonl")]

    # State should be saved
    state_store = RunStateStore(tmp_path)
    state = state_store.load(outcome.run_id)
    assert state is not None
    assert state.run_status == "paused"


def test_engine_can_resume_paused_run(tmp_path: Path):
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"message": payload["message"]})
    gateway = ActionGatewayExecutor(registry)

    # Create agent with multiple decisions
    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "first"},
            ),
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "second"},
            ),
            AgentDecision(
                decision_type="complete",
                final_result={"message": "done"},
            ),
        ]
    )

    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object", "required_keys": ["message"]},
        allowed_actions=["echo"],
    )

    # Pause after first action
    engine.request_pause()
    outcome1 = engine.run(task_spec=spec, task_input={}, agent=agent1)
    run_id = outcome1.run_id
    assert outcome1.run_result.status == "paused"

    # Resume with new agent instance (same decisions)
    agent2 = ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "first"},
            ),
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "second"},
            ),
            AgentDecision(
                decision_type="complete",
                final_result={"message": "done"},
            ),
        ]
    )

    outcome2 = engine.resume(run_id, agent2)

    assert outcome2.run_result.status == "completed"
    assert outcome2.eval_result.passed is True

    # Check trace has all events including pause and resume
    events = read_trace_events(tmp_path / f"{run_id}.jsonl")
    event_types = [e.event_type for e in events]
    assert "run_paused" in event_types
    assert "run_resumed" in event_types
    assert "run_completed" in event_types


def test_resume_fails_for_non_paused_run(tmp_path: Path):
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"message": payload["message"]})
    gateway = ActionGatewayExecutor(registry)
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="complete",
                final_result={"message": "done"},
            ),
        ]
    )
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    outcome = engine.run(task_spec=spec, task_input={}, agent=agent)
    assert outcome.run_result.status == "completed"

    # Try to resume completed run
    import pytest
    with pytest.raises(ValueError, match="No paused state found"):
        engine.resume(outcome.run_id, agent)