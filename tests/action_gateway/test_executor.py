from zheng_agent.core.action_gateway.executor import ActionGatewayExecutor
from zheng_agent.core.action_gateway.registry import ActionAdapterRegistry
from zheng_agent.core.contracts import ActionRequest, TaskSpec


def test_gateway_executes_allowed_action():
    registry = ActionAdapterRegistry()
    registry.register("echo", lambda payload: {"echo": payload["message"]})
    executor = ActionGatewayExecutor(registry)

    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )
    request = ActionRequest(
        run_id="run-1",
        step_id="step-1",
        action_name="echo",
        action_input={"message": "hello"},
        requested_by="mock-agent",
    )

    result = executor.execute(spec, request)

    assert result.status == "success"
    assert result.output == {"echo": "hello"}


def test_gateway_rejects_action_not_in_allowlist():
    registry = ActionAdapterRegistry()
    executor = ActionGatewayExecutor(registry)
    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=[],
    )
    request = ActionRequest(
        run_id="run-1",
        step_id="step-1",
        action_name="echo",
        action_input={"message": "hello"},
        requested_by="mock-agent",
    )

    result = executor.execute(spec, request)

    assert result.status == "rejected"
    assert result.error == "action_not_allowed"