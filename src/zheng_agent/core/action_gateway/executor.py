from zheng_agent.core.action_gateway.policy import ActionPolicy
from zheng_agent.core.action_gateway.registry import ActionAdapterRegistry
from zheng_agent.core.contracts import ActionRequest, ActionResult, TaskSpec


class ActionGatewayExecutor:
    def __init__(self, registry: ActionAdapterRegistry, policy: ActionPolicy | None = None):
        self.registry = registry
        self.policy = policy or ActionPolicy()

    def execute(self, task_spec: TaskSpec, request: ActionRequest) -> ActionResult:
        if not self.policy.is_allowed(task_spec, request):
            return ActionResult(status="rejected", error="action_not_allowed")

        try:
            adapter = self.registry.get(request.action_name)
        except KeyError:
            return ActionResult(status="failed", error="adapter_not_registered")

        try:
            output = adapter(request.action_input)
        except Exception as exc:
            return ActionResult(status="failed", error=str(exc))

        return ActionResult(status="success", output=output)