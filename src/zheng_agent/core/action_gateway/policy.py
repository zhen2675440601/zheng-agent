from zheng_agent.core.contracts import ActionRequest, TaskSpec


class ActionPolicy:
    def is_allowed(self, task_spec: TaskSpec, request: ActionRequest) -> bool:
        return request.action_name in task_spec.allowed_actions