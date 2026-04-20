from zheng_agent.core.contracts import EvalResult, RunResult, TaskSpec
from zheng_agent.core.evaluation.validators import BasicRunEvaluator
from zheng_agent.core.tracing.events import build_trace_event


def test_basic_evaluator_fails_when_required_keys_missing():
    spec = TaskSpec(
        task_type="demo",
        title="演示任务",
        description="最小任务",
        input_schema={"type": "object"},
        output_schema={"type": "object", "required_keys": ["message"]},
        allowed_actions=["echo"],
    )
    result = RunResult(run_id="run-1", task_type="demo", status="completed", output={})
    trace = [
        build_trace_event(
            run_id="run-1",
            step_id=None,
            event_type="run_completed",
            payload={},
            sequence_number=1,
        )
    ]

    evaluation = BasicRunEvaluator().evaluate(spec, trace, result)

    assert isinstance(evaluation, EvalResult)
    assert evaluation.passed is False
    assert any("message" in reason for reason in evaluation.reasons)