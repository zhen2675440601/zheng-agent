from pydantic import ValidationError
import pytest

from zheng_agent.core.contracts import (
    ActionRequest,
    ActionResult,
    AgentDecision,
    DecisionType,
    EvalResult,
    RunContext,
    RunResult,
    TaskSpec,
)


def test_contract_package_exports_decision_type():
    assert DecisionType.__args__ == (
        "request_action",
        "respond",
        "complete",
        "fail",
    )


def test_task_spec_accepts_minimum_fields():
    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    assert spec.max_steps == 20
    assert spec.timeout_seconds is None


def test_agent_decision_requires_action_fields_for_request_action():
    with pytest.raises(ValidationError):
        AgentDecision(decision_type="request_action")


def test_agent_decision_requires_final_result_for_complete():
    with pytest.raises(ValidationError):
        AgentDecision(decision_type="complete")


def test_action_result_rejected_is_distinct_status():
    result = ActionResult(status="rejected", error="not allowed")
    assert result.status == "rejected"


def test_run_context_contains_trace_and_step_index():
    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )

    context = RunContext(run_id="run-1", task_spec=spec, task_input={"x": 1})

    assert context.visible_trace == []
    assert context.step_index == 0