from pydantic import BaseModel, Field

from zheng_agent.core.contracts.task import TaskSpec


class RunContext(BaseModel):
    run_id: str
    task_spec: TaskSpec
    task_input: dict
    visible_trace: list[dict] = Field(default_factory=list)
    step_index: int = 0