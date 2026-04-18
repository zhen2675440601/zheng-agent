from typing import Literal

from pydantic import BaseModel, Field


class RunResult(BaseModel):
    run_id: str
    task_type: str
    status: Literal["completed", "failed"]
    output: dict | None = None
    error: str | None = None


class EvalResult(BaseModel):
    passed: bool
    score: float | None = None
    reasons: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)