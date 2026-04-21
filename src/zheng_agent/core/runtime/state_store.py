from pathlib import Path

from pydantic import BaseModel

from zheng_agent.core.contracts import TaskSpec


class RunState(BaseModel):
    """Persistable state for a paused run."""

    run_id: str
    run_status: str
    step_id: str | None
    step_status: str
    sequence: int
    task_spec: TaskSpec
    task_input: dict
    agent_decisions_index: int = 0  # For ScriptedMockAgent recovery


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