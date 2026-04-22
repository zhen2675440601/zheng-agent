import json

from zheng_agent.core.contracts import RunContext, TaskSpec

SYSTEM_PROMPT = """你是一个任务执行 Agent。你需要根据任务规格和当前状态做出决策。

可用决策类型：
1. request_action - 请求执行一个动作
2. respond - 返回中间响应，但不结束任务
3. advance_step - 当前 step 已完成，推进到下一 step
4. complete - 任务完成，返回结果
5. fail - 任务失败，说明原因

你必须以 JSON 格式回复，格式如下：
- request_action: {"decision_type": "request_action", "reasoning": "...", "action_name": "...", "action_input": {...}}
- respond: {"decision_type": "respond", "reasoning": "...", "response": {...}}
- advance_step: {"decision_type": "advance_step", "reasoning": "..."}
- complete: {"decision_type": "complete", "reasoning": "...", "final_result": {...}}
- fail: {"decision_type": "fail", "reasoning": "...", "failure_reason": "..."}
"""


def build_decision_prompt(task_spec: TaskSpec, run_context: RunContext) -> str:
    """构造决策 prompt"""
    task_info = f"""## 任务规格
- 类型: {task_spec.task_type}
- 标题: {task_spec.title}
- 描述: {task_spec.description}
- 输入 Schema: {json.dumps(task_spec.input_schema, ensure_ascii=False)}
- 输出 Schema: {json.dumps(task_spec.output_schema, ensure_ascii=False)}
- 允许的动作: {json.dumps(task_spec.allowed_actions, ensure_ascii=False)}
- 约束: {json.dumps(task_spec.constraints, ensure_ascii=False)}
- 成功标准: {json.dumps(task_spec.success_criteria, ensure_ascii=False)}
- 最大步数: {task_spec.max_steps}"""

    context_info = f"""## 当前上下文
- Run ID: {run_context.run_id}
- 当前步数: {run_context.step_index}
- 任务输入: {json.dumps(run_context.task_input, ensure_ascii=False)}"""

    trace_info = ""
    if run_context.visible_trace:
        # 只显示最近5条事件
        recent_trace = run_context.visible_trace[-5:]
        trace_info = f"""## 执行轨迹
{json.dumps(recent_trace, ensure_ascii=False, indent=2)}"""

    return f"{SYSTEM_PROMPT}\n\n{task_info}\n\n{context_info}\n{trace_info}\n\n请做出决策："