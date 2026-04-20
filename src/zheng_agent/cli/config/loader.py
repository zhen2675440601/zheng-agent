import json
from pathlib import Path

import yaml

from zheng_agent.core.contracts import TaskSpec, validate_input


class ValidationError(Exception):
    """Raised when input/output validation fails."""
    pass


def load_task_spec(path: Path) -> TaskSpec:
    """从 YAML 文件加载 TaskSpec"""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TaskSpec.model_validate(data)


def load_and_validate_task_input(spec: TaskSpec, path: Path) -> dict:
    """从 YAML/JSON 文件加载 task_input 并验证"""
    data = load_task_input(path)
    valid, errors = validate_input(spec.input_schema, data)
    if not valid:
        raise ValidationError(f"Input validation failed: {errors}")
    return data


def load_task_input(path: Path) -> dict:
    """从 YAML/JSON 文件加载 task_input"""
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as f:
        if suffix in [".yaml", ".yml"]:
            return yaml.safe_load(f)
        elif suffix == ".json":
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")