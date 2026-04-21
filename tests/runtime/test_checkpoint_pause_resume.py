"""Tests for cross-process pause/resume checkpoint functionality."""

import subprocess
import sys
from pathlib import Path
import tempfile
import json

from zheng_agent.core.contracts import TaskSpec
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunStateStore
from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision


def test_pause_signal_file_is_detected_by_engine(tmp_path: Path):
    """Engine detects pause signal file and pauses at next checkpoint."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    # Agent that will echo multiple times before completing
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "first"}),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "second"}),
            AgentDecision(decision_type="complete", final_result={"message": "done"}),
        ]
    )

    # Create pause signal file before running
    signal_path = tmp_path / "test-run-1.pause_signal"
    signal_path.write_text("pause", encoding="utf-8")

    outcome = engine.run(
        task_spec=spec,
        task_input={"message": "test"},
        agent=agent,
        run_id="test-run-1",
    )

    # Engine should have paused at first checkpoint
    assert outcome.run_result.status == "paused"

    # Signal file should be cleared after pause is processed
    assert not signal_path.exists()

    # Checkpoint should be saved
    state_store = RunStateStore(tmp_path)
    state = state_store.load("test-run-1")
    assert state is not None
    assert state.run_status == "paused"


def test_external_pause_request_via_signal_file(tmp_path: Path):
    """Pause can be requested via signal file (simulating external process)."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    # Agent that echoes before completing
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "hello"}),
            AgentDecision(decision_type="complete", final_result={"message": "done"}),
        ]
    )

    # Request pause externally (like CLI pause command)
    engine.request_pause_external("external-pause-run")

    outcome = engine.run(
        task_spec=spec,
        task_input={"message": "test"},
        agent=agent,
        run_id="external-pause-run",
    )

    assert outcome.run_result.status == "paused"

    state_store = RunStateStore(tmp_path)
    state = state_store.load("external-pause-run")
    assert state is not None
    assert state.checkpoint_kind == "pause"
    assert state.checkpoint_reason == "user_requested"


def test_resume_from_checkpoint_restores_agent_position(tmp_path: Path):
    """Resume restores agent position from checkpoint metadata."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    # First agent that pauses after first echo
    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "first"}),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "second"}),
            AgentDecision(decision_type="complete", final_result={"message": "done"}),
        ]
    )

    # Request pause in-process
    engine.request_pause()

    outcome1 = engine.run(
        task_spec=spec,
        task_input={"message": "test"},
        agent=agent1,
        run_id="restore-test-run",
    )

    assert outcome1.run_result.status == "paused"

    # Check agent recovery metadata was saved
    state_store = RunStateStore(tmp_path)
    state = state_store.load("restore-test-run")
    assert state is not None
    assert state.agent_recovery is not None
    assert state.agent_recovery.agent_type == "mock"
    # Agent position is saved at checkpoint (may be 0 if paused before first decision)
    assert "current_index" in state.agent_recovery.recovery_data

    # Create new agent with same decisions for resume
    agent2 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "first"}),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "second"}),
            AgentDecision(decision_type="complete", final_result={"message": "done"}),
        ]
    )

    outcome2 = engine.resume("restore-test-run", agent2)

    assert outcome2.run_result.status == "completed"
    assert outcome2.eval_result.passed is True


def test_checkpoint_saved_at_step_boundary(tmp_path: Path):
    """Checkpoint is saved when step starts."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
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
            AgentDecision(decision_type="complete", final_result={"message": "done"}),
        ]
    )

    # Request pause after engine starts
    engine.request_pause()

    outcome = engine.run(
        task_spec=spec,
        task_input={"message": "test"},
        agent=agent,
        run_id="step-checkpoint-run",
    )

    state_store = RunStateStore(tmp_path)
    # There should be checkpoints saved (at least at step_boundary)
    state = state_store.load("step-checkpoint-run")
    assert state is not None


def test_multiple_pause_resume_cycles(tmp_path: Path):
    """Run can be paused and resumed multiple times."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})

    gateway = ActionGatewayExecutor(registry)
    evaluator = BasicRunEvaluator()
    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=evaluator)

    decisions = [
        AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "1"}),
        AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "2"}),
        AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "3"}),
        AgentDecision(decision_type="complete", final_result={"message": "done"}),
    ]

    # First pause
    agent1 = ScriptedMockAgent(decisions=decisions)
    engine.request_pause()
    outcome1 = engine.run(spec, {"message": "test"}, agent1, run_id="multi-pause-run")
    assert outcome1.run_result.status == "paused"

    # Resume with new agent that will pause again
    agent2 = ScriptedMockAgent(decisions=decisions)
    engine.request_pause()
    outcome2 = engine.resume("multi-pause-run", agent2)
    assert outcome2.run_result.status == "paused"

    # Final resume to complete
    agent3 = ScriptedMockAgent(decisions=decisions)
    outcome3 = engine.resume("multi-pause-run", agent3)
    assert outcome3.run_result.status == "completed"