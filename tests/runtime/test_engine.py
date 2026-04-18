from pathlib import Path

from zheng_agent.core.action_gateway import ActionAdapterRegistry, ActionGatewayExecutor
from zheng_agent.core.agent.mock import ScriptedMockAgent
from zheng_agent.core.contracts import AgentDecision, TaskSpec
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.runtime.engine import HarnessEngine
from zheng_agent.core.tracing.reader import read_trace_events


def test_engine_completes_run_with_action(tmp_path: Path):
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"message": payload["message"]})
    gateway = ActionGatewayExecutor(registry)
    agent = ScriptedMockAgent(
        decisions=[
            AgentDecision(
                decision_type="request_action",
                action_name="echo",
                action_input={"message": "hello"},
            ),
            AgentDecision(
                decision_type="complete",
                final_result={"message": "hello"},
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

    outcome = engine.run(task_spec=spec, task_input={"message": "hello"}, agent=agent)
    events = read_trace_events(tmp_path / f"{outcome.run_id}.jsonl")

    assert outcome.run_result.status == "completed"
    assert outcome.eval_result.passed is True
    assert [event.event_type for event in events] == [
        "run_created",
        "run_validated",
        "run_prepared",
        "run_started",
        "step_scheduled",
        "step_started",
        "agent_decision_produced",
        "action_requested",
        "action_approved",
        "action_executed",
        "agent_decision_produced",
        "step_completed",
        "run_completed",
        "evaluation_completed",
    ]