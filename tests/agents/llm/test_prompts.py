import json

from zheng_agent.agents.llm.prompts import build_decision_prompt
from zheng_agent.core.contracts import RunContext, TaskSpec


def test_build_decision_prompt_includes_task_spec():
    spec = TaskSpec(
        task_type="demo",
        title="Demo Task",
        description="A demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo", "log"],
    )
    context = RunContext(run_id="run-1", task_spec=spec, task_input={})

    prompt = build_decision_prompt(spec, context)

    # 新 prompt 显示 title 而非 task_type
    assert "Demo Task" in prompt
    assert "echo" in prompt
    assert "log" in prompt
    # 显示允许动作列表
    assert "允许动作" in prompt


def test_build_decision_prompt_includes_task_input():
    spec = TaskSpec(
        task_type="demo",
        title="Demo Task",
        description="A demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )
    context = RunContext(run_id="run-1", task_spec=spec, task_input={"message": "hello"})

    prompt = build_decision_prompt(spec, context)

    assert "hello" in prompt


def test_build_decision_prompt_includes_visible_trace():
    spec = TaskSpec(
        task_type="demo",
        title="Demo Task",
        description="A demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )
    context = RunContext(
        run_id="run-1",
        task_spec=spec,
        task_input={},
        visible_trace=[{"event_type": "action_executed", "payload": {"output": {"result": "ok"}}}],
    )

    prompt = build_decision_prompt(spec, context)

    assert "action_executed" in prompt


def test_build_decision_prompt_truncates_long_trace():
    spec = TaskSpec(
        task_type="demo",
        title="Demo Task",
        description="A demo task",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        allowed_actions=["echo"],
    )
    long_trace = [{"event_type": f"event_{i}", "payload": {}} for i in range(10)]
    context = RunContext(run_id="run-1", task_spec=spec, task_input={}, visible_trace=long_trace)

    prompt = build_decision_prompt(spec, context)

    # Should only include last 5 events
    assert "event_9" in prompt
    assert "event_0" not in prompt