from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from zheng_agent.core.contracts import TaskSpec
from zheng_agent.core.contracts.recovery import AgentRecoveryMetadata, AgentType, RuntimeMode, CheckpointKind


class RunState(BaseModel):
    """Versioned checkpoint snapshot for run recovery."""

    version: int = 1

    run_id: str
    run_status: str

    step_id: str | None
    step_status: str
    step_index: int = 0

    sequence: int
    last_event_id: str | None = None

    task_spec: TaskSpec
    task_input: dict

    agent_recovery: AgentRecoveryMetadata | None = None

    runtime_mode: RuntimeMode = "default"

    checkpoint_kind: CheckpointKind = "pause"
    checkpoint_reason: str | None = None


class RunStateStore:
    """Store and retrieve run states for pause/resume."""

    def __init__(self, state_root: Path):
        self.state_root = state_root
        self.state_root.mkdir(parents=True, exist_ok=True)

    def _state_path(self, run_id: str) -> Path:
        return self.state_root / f"{run_id}_state.json"

    def save(self, state: RunState) -> None:
        path = self._state_path(state.run_id)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load(self, run_id: str) -> RunState | None:
        path = self._state_path(run_id)
        if not path.exists():
            return None
        return RunState.model_validate_json(path.read_text(encoding="utf-8"))

    def delete(self, run_id: str) -> None:
        path = self._state_path(run_id)
        if path.exists():
            path.unlink()