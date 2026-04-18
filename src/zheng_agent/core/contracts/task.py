from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    task_type: str
    title: str
    description: str
    input_schema: dict
    output_schema: dict
    allowed_actions: list[str]
    constraints: dict = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    max_steps: int = 20
    timeout_seconds: int | None = None