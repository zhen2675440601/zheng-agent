import pytest
from pathlib import Path

from zheng_agent.cli.config.loader import load_task_spec, load_task_input


def test_load_task_spec_from_yaml(tmp_path: Path):
    yaml_content = """
task_type: demo
title: Demo Task
description: A demo task
input_schema:
  type: object
output_schema:
  type: object
allowed_actions:
  - echo
"""
    yaml_file = tmp_path / "task_spec.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    spec = load_task_spec(yaml_file)

    assert spec.task_type == "demo"
    assert spec.title == "Demo Task"
    assert spec.allowed_actions == ["echo"]


def test_load_task_spec_missing_required_field(tmp_path: Path):
    yaml_content = """
title: Demo Task
description: A demo task
"""
    yaml_file = tmp_path / "invalid_spec.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(Exception):
        load_task_spec(yaml_file)


def test_load_task_input_from_yaml(tmp_path: Path):
    yaml_content = """
message: hello
count: 3
"""
    yaml_file = tmp_path / "input.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    data = load_task_input(yaml_file)

    assert data["message"] == "hello"
    assert data["count"] == 3


def test_load_task_input_from_json(tmp_path: Path):
    import json

    json_file = tmp_path / "input.json"
    json_file.write_text(json.dumps({"message": "hello", "count": 3}), encoding="utf-8")

    data = load_task_input(json_file)

    assert data["message"] == "hello"
    assert data["count"] == 3


def test_load_task_input_unsupported_format(tmp_path: Path):
    txt_file = tmp_path / "input.txt"
    txt_file.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_task_input(txt_file)