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

## 核心规则

### 动作规则
- 只调用"允许的动作"列表中的动作
- action_input 必须使用真实数据（从任务输入或已有结果中获取）

### 循环避免（重要）
- **禁止重复执行相同动作** - 如果某动作已执行过，不要再重复调用
- **使用多种动作** - 每个动作只调用一次，按任务流程依次使用不同动作
- **不要在同一 step 内无限循环** - 调用过动作后就推进状态

### 状态推进
- **advance_step**: 当前 step 的目标已达成（如数据已获取），进入下一 step 继续处理
- **complete**: 所有输出已准备好，立即返回 final_result 结束任务
- 输出准备好后直接 complete，不要再 advance_step

### 决策策略
1. 先看"已执行动作"历史，避免重复
2. 选择下一个未执行的允许动作
3. 所有动作都执行完后，整理结果并 complete
"""


def _extract_executed_actions(visible_trace: list[dict]) -> list[str]:
    """从 trace 中提取已执行的动作名称"""
    executed = []
    for event in visible_trace:
        # action_requested 和 action_approved 都有 action_name
        if event.get("event_type") in ("action_requested", "action_approved"):
            action_name = event.get("payload", {}).get("action_name")
            if action_name and action_name not in executed:
                executed.append(action_name)
    return executed


def build_decision_prompt(task_spec: TaskSpec, run_context: RunContext) -> str:
    """构造决策 prompt"""
    allowed = list(task_spec.allowed_actions)
    required = ", ".join(task_spec.output_schema.get("required_keys", [])) or "无"

    # 提取已执行动作
    executed = _extract_executed_actions(run_context.visible_trace)
    remaining = [a for a in allowed if a not in executed]

    # 构建状态信息
    task = f"任务: {task_spec.title}"
    ctx = f"Step: {run_context.step_index + 1}/{task_spec.max_steps}"
    input_info = f"输入: {json.dumps(run_context.task_input, ensure_ascii=False)}"

    # 动作状态
    action_status = f"允许动作: {', '.join(allowed)}"
    if executed:
        action_status += f"\n已执行: {', '.join(executed)}"
    if remaining:
        action_status += f"\n待执行: {', '.join(remaining)}"
    else:
        action_status += "\n待执行: 无（所有动作已执行完）"

    # 最近结果
    recent = ""
    if run_context.visible_trace[-3:]:
        recent = f"最近事件: {json.dumps(run_context.visible_trace[-3:], ensure_ascii=False)}"

    # 决策引导
    if remaining:
        guide = f"下一步建议: 执行 '{remaining[0]}' → request_action"
    elif executed:
        guide = f"下一步建议: 整理结果 → complete(包含: {required})"
    else:
        guide = f"下一步: request_action 或 advance_step"

    parts = [SYSTEM_PROMPT, "", task, ctx, input_info, action_status]
    if recent:
        parts.append(recent)
    parts.append("")
    parts.append(guide)

    return "\n".join(parts)