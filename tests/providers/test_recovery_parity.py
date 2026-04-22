"""Tests for provider-grade recovery parity across mock and openai."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision, RunContext, TaskSpec
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata, RecoveryError
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.runtime.state_store import RunState, RunStateStore
from zheng_agent.core.tracing import read_trace_events


@pytest.fixture
def mock_spec():
    return TaskSpec(
        task_type="parity_test",
        title="Parity Test",
        description="Test provider recovery parity",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
        max_steps=10,
    )


@pytest.fixture
def gateway():
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echoed": payload.get("message", "")})
    return ActionGatewayExecutor(registry)


class MockOpenAIClient:
    """Test double for OpenAI client."""

    def __init__(self, responses: list[str]):
        self._responses = responses
        self._index = 0

    class MockCompletions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, **kwargs):
            response = self._parent._responses[self._parent._index]
            self._parent._index += 1
            return type(
                "MockResponse",
                (),
                {
                    "choices": [
                        type(
                            "MockChoice",
                            (),
                            {"message": type("MockMessage", (), {"content": response})()},
                        )()
                    ]
                },
            )()

    @property
    def chat(self):
        return type("MockChat", (), {"completions": self.MockCompletions(self)})()


def test_mock_recovery_metadata_is_complete(mock_spec, gateway, tmp_path: Path):
    """Mock agent recovery metadata contains all required fields."""
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "hi"}),
            AgentDecision(decision_type="complete", final_result={"done": True}),
        ]
    )

    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=BasicRunEvaluator())
    engine.request_pause()
    outcome = engine.run(mock_spec, {}, agent, run_id="mock-recovery-check")

    state = engine.get_state("mock-recovery-check")
    assert state is not None
    assert state.agent_recovery is not None
    assert state.agent_recovery.agent_type == "mock"

    recovery_data = state.agent_recovery.recovery_data
    assert "decisions" in recovery_data
    assert "current_index" in recovery_data
    assert len(recovery_data["decisions"]) == 2
    assert recovery_data["current_index"] >= 0


def test_mock_recovery_roundtrip_preserves_decisions(mock_spec, gateway, tmp_path: Path):
    """Mock agent can restore from checkpoint and continue correctly."""
    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "step1"}),
            AgentDecision(decision_type="complete", final_result={"steps": 1}),
        ]
    )

    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=BasicRunEvaluator())
    engine.request_pause()
    outcome1 = engine.run(mock_spec, {}, agent1, run_id="mock-roundtrip")

    assert outcome1.run_result.status == "paused"

    state = engine.get_state("mock-roundtrip")
    agent2 = ScriptedMockAgent(decisions=[])
    agent2.restore_from_metadata(state.agent_recovery)

    outcome2 = engine.resume("mock-roundtrip", agent2)
    assert outcome2.run_result.status == "completed"
    assert outcome2.run_result.output["steps"] == 1


def test_mock_recovery_validation_rejects_missing_decisions():
    """Mock recovery validation fails when decisions are missing."""
    metadata = AgentRecoveryMetadata(
        agent_type="mock",
        recovery_data={"current_index": 0},
    )

    with pytest.raises(RecoveryError, match="missing serialized decisions"):
        metadata.validate_for_restore()


def test_mock_recovery_validation_rejects_missing_index():
    """Mock recovery validation fails when current_index is missing."""
    metadata = AgentRecoveryMetadata(
        agent_type="mock",
        recovery_data={"decisions": [{"decision_type": "complete"}]},
    )

    with pytest.raises(RecoveryError, match="missing current_index"):
        metadata.validate_for_restore()


def test_openai_recovery_metadata_contains_required_fields():
    """OpenAI agent recovery metadata contains model and history."""
    from zheng_agent.agents.llm.openai_agent import OpenAIAgent

    agent = OpenAIAgent(model="gpt-4o", temperature=0.5)
    agent._message_history = [{"role": "assistant", "content": '{"decision_type": "complete"}'}]
    agent._last_prompt_context = {"task_type": "test", "step_index": 0}

    metadata = agent.get_recovery_metadata()
    assert metadata.agent_type == "openai"
    assert metadata.recovery_data["model"] == "gpt-4o"
    assert metadata.recovery_data["temperature"] == 0.5
    assert "message_history" in metadata.recovery_data
    assert "last_prompt_context" in metadata.recovery_data


def test_openai_recovery_validation_rejects_missing_model():
    """OpenAI recovery validation fails when model is missing."""
    metadata = AgentRecoveryMetadata(
        agent_type="openai",
        recovery_data={"temperature": 0.5, "message_history": []},
    )

    with pytest.raises(RecoveryError, match="missing model"):
        metadata.validate_for_restore()


def test_openai_agent_can_restore_from_metadata():
    """OpenAI agent restores model, temperature, and history from metadata."""
    from zheng_agent.agents.llm.openai_agent import OpenAIAgent

    agent1 = OpenAIAgent(model="gpt-4o-mini", temperature=0.3)
    agent1._message_history = [{"role": "assistant", "content": "test"}]
    agent1._last_prompt_context = {"task_type": "demo"}

    metadata = agent1.get_recovery_metadata()

    agent2 = OpenAIAgent()
    agent2.restore_from_metadata(metadata)

    assert agent2.model == "gpt-4o-mini"
    assert agent2.temperature == 0.3
    assert agent2._message_history == [{"role": "assistant", "content": "test"}]
    assert agent2._last_prompt_context == {"task_type": "demo"}


def test_recovery_after_action_checkpoint_continues_correctly(mock_spec, gateway, tmp_path: Path):
    """Recovery from action_before checkpoint continues with correct action sequence."""
    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "first"}),
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "second"}),
            AgentDecision(decision_type="complete", final_result={"count": 2}),
        ]
    )

    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=BasicRunEvaluator())
    engine.request_pause()
    outcome1 = engine.run(mock_spec, {}, agent1, run_id="action-checkpoint-test")

    state = engine.get_state("action-checkpoint-test")
    assert state.checkpoint_kind == "step_boundary" or state.checkpoint_kind == "pause"

    agent2 = ScriptedMockAgent(decisions=[])
    agent2.restore_from_metadata(state.agent_recovery)

    outcome2 = engine.resume("action-checkpoint-test", agent2)
    assert outcome2.run_result.status == "completed"

    events = read_trace_events(tmp_path / "action-checkpoint-test.jsonl")
    action_executed = [e for e in events if e.event_type == "action_executed"]
    assert len(action_executed) >= 2


def test_resumed_run_trace_sequence_is_contiguous(mock_spec, gateway, tmp_path: Path):
    """Resumed run trace has contiguous sequence numbers."""
    agent1 = ScriptedMockAgent(
        decisions=[
            AgentDecision(decision_type="request_action", action_name="echo", action_input={"message": "a"}),
            AgentDecision(decision_type="complete", final_result={"ok": True}),
        ]
    )

    engine = HarnessEngine(trace_root=tmp_path, gateway=gateway, evaluator=BasicRunEvaluator())
    engine.request_pause()
    outcome1 = engine.run(mock_spec, {}, agent1, run_id="trace-contiguous")

    agent2 = ScriptedMockAgent(decisions=[])
    agent2.restore_from_metadata(engine.get_state("trace-contiguous").agent_recovery)

    outcome2 = engine.resume("trace-contiguous", agent2)

    events = read_trace_events(tmp_path / "trace-contiguous.jsonl")
    sequence_numbers = [e.sequence_number for e in events]
    assert sequence_numbers == sorted(sequence_numbers)
    assert sequence_numbers[0] == 1
    assert sequence_numbers[-1] == len(events)


def test_mock_recovery_rejects_wrong_agent_type():
    """Mock agent raises RecoveryError when restoring from openai metadata."""
    agent = ScriptedMockAgent(decisions=[AgentDecision(decision_type="complete", final_result={})])

    metadata = AgentRecoveryMetadata(
        agent_type="openai",
        recovery_data={"model": "gpt-4o"},
    )

    with pytest.raises(RecoveryError, match="metadata agent_type mismatch"):
        agent.restore_from_metadata(metadata)


def test_openai_recovery_rejects_wrong_agent_type():
    """OpenAI agent raises RecoveryError when restoring from mock metadata."""
    from zheng_agent.agents.llm.openai_agent import OpenAIAgent

    agent = OpenAIAgent()

    metadata = AgentRecoveryMetadata(
        agent_type="mock",
        recovery_data={"decisions": [], "current_index": 0},
    )

    with pytest.raises(RecoveryError, match="metadata agent_type mismatch"):
        agent.restore_from_metadata(metadata)