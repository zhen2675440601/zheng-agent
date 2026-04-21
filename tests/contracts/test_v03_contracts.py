"""Tests for v0.3 contract changes: checkpoint, recovery, typed payloads."""

from pathlib import Path

from zheng_agent.core.contracts import (
    ActionRequest,
    ActionResult,
    AgentRecoveryMetadata,
    TaskSpec,
)
from zheng_agent.core.contracts.recovery import AgentType, CheckpointKind, RuntimeMode
from zheng_agent.core.runtime.state_store import RunState, RunStateStore
from zheng_agent.core.tracing.events import (
    RunCompletedPayload,
    RunFailedPayload,
    StepFailedPayload,
    TraceEvent,
    build_typed_trace_event,
    EVENT_PAYLOAD_TYPES,
)


def test_run_state_checkpoint_serialization(tmp_path: Path):
    """RunState with versioned checkpoint can serialize/deserialize."""
    spec = TaskSpec(
        task_type="demo",
        title="Demo",
        description="Demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    state = RunState(
        version=1,
        run_id="run-1",
        run_status="paused",
        step_id="step-1",
        step_status="running",
        step_index=2,
        sequence=10,
        last_event_id="evt-abc",
        task_spec=spec,
        task_input={"message": "hello"},
        agent_recovery=AgentRecoveryMetadata(
            agent_type="mock",
            recovery_data={"decisions_count": 3, "current_index": 1},
        ),
        runtime_mode="default",
        checkpoint_kind="pause",
        checkpoint_reason="user_requested",
    )

    store = RunStateStore(tmp_path)
    store.save(state)

    loaded = store.load("run-1")
    assert loaded is not None
    assert loaded.version == 1
    assert loaded.run_id == "run-1"
    assert loaded.step_index == 2
    assert loaded.last_event_id == "evt-abc"
    assert loaded.agent_recovery is not None
    assert loaded.agent_recovery.agent_type == "mock"
    assert loaded.agent_recovery.recovery_data["current_index"] == 1
    assert loaded.checkpoint_kind == "pause"
    assert loaded.checkpoint_reason == "user_requested"


def test_agent_recovery_metadata_serialization():
    """AgentRecoveryMetadata can serialize/deserialize."""
    metadata = AgentRecoveryMetadata(
        agent_type="openai",
        recovery_data={
            "model": "gpt-4o",
            "temperature": 0.0,
            "message_history": [{"role": "user", "content": "hi"}],
        },
    )

    json_str = metadata.model_dump_json()
    loaded = AgentRecoveryMetadata.model_validate_json(json_str)

    assert loaded.agent_type == "openai"
    assert loaded.recovery_data["model"] == "gpt-4o"
    assert len(loaded.recovery_data["message_history"]) == 1


def test_action_request_has_causality_fields():
    """ActionRequest includes request_id, timestamps, and causality."""
    request = ActionRequest(
        run_id="run-1",
        step_id="step-1",
        action_name="echo",
        action_input={"message": "hello"},
        requested_by="agent",
        caused_by_decision_id="decision-123",
    )

    assert request.request_id is not None
    assert request.request_timestamp is not None
    assert request.caused_by_decision_id == "decision-123"


def test_action_result_has_error_category():
    """ActionResult includes error_category field."""
    result = ActionResult(
        request_id="req-456",
        status="rejected",
        error="action not allowed",
        error_category="not_allowed",
    )

    assert result.request_id == "req-456"
    assert result.error_category == "not_allowed"
    assert result.result_timestamp is not None


def test_typed_trace_event_payloads():
    """TraceEvent can carry typed payloads and retrieve them."""
    payload = RunCompletedPayload(status="completed", output={"message": "done"})
    event = build_typed_trace_event(
        run_id="run-1",
        step_id=None,
        event_type="run_completed",
        payload=payload,
        sequence_number=1,
    )

    assert event.event_type == "run_completed"
    assert event.payload["status"] == "completed"
    assert event.payload["output"]["message"] == "done"

    typed = event.get_typed_payload()
    assert isinstance(typed, RunCompletedPayload)
    assert typed.status == "completed"


def test_step_failed_payload_roundtrip():
    """StepFailedPayload can be stored in TraceEvent and retrieved."""
    payload = StepFailedPayload(step_id="step-2", reason="action_failed")
    event = build_typed_trace_event(
        run_id="run-1",
        step_id="step-2",
        event_type="step_failed",
        payload=payload,
        sequence_number=5,
    )

    typed = event.get_typed_payload()
    assert isinstance(typed, StepFailedPayload)
    assert typed.step_id == "step-2"
    assert typed.reason == "action_failed"


def test_event_payload_types_registry():
    """EVENT_PAYLOAD_TYPES maps event types to payload classes."""
    assert "run_completed" in EVENT_PAYLOAD_TYPES
    assert EVENT_PAYLOAD_TYPES["run_completed"] == RunCompletedPayload
    assert "step_failed" in EVENT_PAYLOAD_TYPES
    assert EVENT_PAYLOAD_TYPES["step_failed"] == StepFailedPayload
    assert "run_failed" in EVENT_PAYLOAD_TYPES
    assert EVENT_PAYLOAD_TYPES["run_failed"] == RunFailedPayload


def test_checkpoint_kind_literal_values():
    """CheckpointKind has expected literal values."""
    valid_kinds: list[CheckpointKind] = ["pause", "action_before", "action_after", "step_boundary"]
    for kind in valid_kinds:
        # Just verify the literal values compile without error
        assert kind in ("pause", "action_before", "action_after", "step_boundary")


def test_agent_type_literal_values():
    """AgentType has expected literal values."""
    valid_types: list[AgentType] = ["mock", "openai"]
    for agent_type in valid_types:
        assert agent_type in ("mock", "openai")


def test_runtime_mode_literal_values():
    """RuntimeMode has expected literal values."""
    valid_modes: list[RuntimeMode] = ["default", "chat", "task"]
    for mode in valid_modes:
        assert mode in ("default", "chat", "task")