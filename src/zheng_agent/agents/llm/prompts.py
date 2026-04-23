import json

from zheng_agent.core.contracts import RunContext, TaskSpec

SYSTEM_PROMPT = """你是任务执行 Agent。根据任务规格执行并返回结果。

## 决策类型

1. **request_action** - 调用允许的动作
   {"decision_type": "request_action", "reasoning": "...", "action_name": "...", "action_input": {...}}

2. **advance_step** - 当前 step 完成，进入下一 step
   {"decision_type": "advance_step", "reasoning": "..."}

3. **complete** - 任务完成，返回结果（立即结束）
   {"decision_type": "complete", "reasoning": "...", "final_result": {...}}

4. **fail** - 无法继续
   {"decision_type": "fail", "reasoning": "...", "failure_reason": "..."}

## 规则

- 只用"允许的动作"
- action_input 用真实数据
- 结果准备好后立即 complete，不要再 advance_step
"""


def build_decision_prompt(task_spec: TaskSpec, run_context: RunContext) -> str:
    """构造决策 prompt"""
    allowed = ", ".join(task_spec.allowed_actions)
    required = ", ".join(task_spec.output_schema.get("required_keys", [])) or "无"

    task = f"任务: {task_spec.title}\n动作: {allowed}\n输出: {required}"
    ctx = f"Step: {run_context.step_index + 1}/{task_spec.max_steps}\n输入: {json.dumps(run_context.task_input, ensure_ascii=False)}"

    trace = ""
    if run_context.visible_trace[-3:]:
        trace = f"最近: {json.dumps(run_context.visible_trace[-3:], ensure_ascii=False)}"

    guide = f"决策: 继续→request_action | step完→advance_step | 结果好→complete(含:{required})"

    return f"{SYSTEM_PROMPT}\n\n{task}\n{ctx}\n{trace}\n\n{guide}"