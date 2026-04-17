# Agent Harness v0.1 State Machine Specification

## 1. Run 状态机

### RunStatus
```python
RunStatus = Literal[
    "created",
    "validated",
    "ready",
    "running",
    "waiting_action",
    "paused",
    "completed",
    "failed",
    "cancelled",
]
```

### 状态定义

| 状态 | 含义 |
|---|---|
| `created` | run 已创建，还未校验 |
| `validated` | 输入和契约校验通过 |
| `ready` | 可以开始执行 |
| `running` | 正在执行某个 step |
| `waiting_action` | 等待 action gateway 执行或返回 |
| `paused` | 被人工或系统暂停 |
| `completed` | 成功完成 |
| `failed` | 执行失败 |
| `cancelled` | 被取消 |

### Run 状态迁移表

| 当前状态 | 事件 | 下一状态 | 说明 |
|---|---|---|---|
| `created` | `validate_passed` | `validated` | 输入、契约通过 |
| `created` | `validate_failed` | `failed` | 初始校验失败 |
| `validated` | `prepare_run` | `ready` | 初始化上下文完成 |
| `ready` | `start_run` | `running` | 进入首个 step |
| `running` | `action_requested` | `waiting_action` | agent 请求外部动作 |
| `waiting_action` | `action_completed` | `running` | 动作完成，恢复执行 |
| `running` | `pause_requested` | `paused` | 人工或系统暂停 |
| `paused` | `resume_requested` | `running` | 恢复执行 |
| `running` | `run_succeeded` | `completed` | 最终结果通过 |
| `running` | `run_failed` | `failed` | 不可恢复失败 |
| `waiting_action` | `action_rejected` | `failed` | action 非法或策略拒绝 |
| `waiting_action` | `action_failed` | `failed` | action 执行失败且不重试 |
| `created`/`validated`/`ready`/`running`/`waiting_action`/`paused` | `cancel_requested` | `cancelled` | 用户或系统取消 |

### Run 状态机约束

1. `completed`、`failed`、`cancelled` 是终态
2. 终态不能再迁移
3. `waiting_action` 只能由 `running` 进入
4. `resume_requested` 只能从 `paused` 触发

### 非法场景
- `created -> running`
- `completed -> running`
- `waiting_action -> completed`
- `failed -> ready`

---

## 2. Step 状态机

### StepStatus
```python
StepStatus = Literal[
    "pending",
    "ready",
    "running",
    "waiting_action",
    "completed",
    "failed",
]
```

### 状态定义

| 状态 | 含义 |
|---|---|
| `pending` | 已存在但未进入执行队列 |
| `ready` | 可执行 |
| `running` | 正在调用 agent 或处理结果 |
| `waiting_action` | step 内部等待 action 结果 |
| `completed` | step 完成 |
| `failed` | step 失败 |

### Step 状态迁移表

| 当前状态 | 事件 | 下一状态 | 说明 |
|---|---|---|---|
| `pending` | `step_scheduled` | `ready` | 被调度 |
| `ready` | `step_started` | `running` | 开始执行 |
| `running` | `decision_request_action` | `waiting_action` | agent 请求 action |
| `waiting_action` | `action_completed` | `running` | action 返回，继续当前 step |
| `running` | `decision_respond` | `completed` | 产出中间响应并结束该 step |
| `running` | `decision_complete` | `completed` | 完成该 step |
| `running` | `decision_fail` | `failed` | agent 显式失败 |
| `waiting_action` | `action_rejected` | `failed` | action 被拒绝 |
| `waiting_action` | `action_failed` | `failed` | action 执行失败 |
| `ready`/`running`/`waiting_action` | `step_error` | `failed` | 系统异常 |

### Step 状态机约束

1. 每个 step attempt 只能有一个终态：`completed` 或 `failed`
2. `waiting_action` 不能直接跳回 `ready`
3. 同一个 attempt 不能重复 `step_started`
4. step 的完成必须先有对应 trace 事件

---

## 3. Run 与 Step 的联动规则

### 规则 1
当 run 进入 `running`，必须至少有一个 step 进入 `ready` 或 `running`

### 规则 2
当 step 进入 `waiting_action`，run 同步进入 `waiting_action`

### 规则 3
当 action 完成后：
- step 从 `waiting_action -> running`
- run 从 `waiting_action -> running`

### 规则 4
当某个 step `completed`：
- 若存在后继 step，则下一个 step 进入 `ready`
- 若无后继且结果满足 contract，则 run `completed`

### 规则 5
当 step `failed`：
- 若策略为 fail-fast，则 run `failed`
- 若未来支持 retry，则进入新的 attempt；v0.1 可先不做 retry

---

## 4. 事件驱动模型

建议状态机通过事件推进，而不是直接改值。

### 核心 Run 事件
```python
RunEvent = Literal[
    "validate_passed",
    "validate_failed",
    "prepare_run",
    "start_run",
    "action_requested",
    "action_completed",
    "action_rejected",
    "action_failed",
    "pause_requested",
    "resume_requested",
    "run_succeeded",
    "run_failed",
    "cancel_requested",
]
```

### 核心 Step 事件
```python
StepEvent = Literal[
    "step_scheduled",
    "step_started",
    "decision_request_action",
    "decision_respond",
    "decision_complete",
    "decision_fail",
    "action_completed",
    "action_rejected",
    "action_failed",
    "step_error",
]
```

---

## 5. v0.1 推荐简化策略

### 先不做
- retry 状态
- waiting_human 状态
- 并行 step 汇聚状态
- 补偿事务状态

### v0.1 只做
- 单 run
- 单活动 step
- action 等待
- pause/resume
- fail-fast

---

## 6. 实现建议

建议最先落地：
- `core/state_machine/run_state.py`
- `core/state_machine/step_state.py`
- `core/state_machine/transitions.py`

迁移表建议显式实现，例如：

```python
ALLOWED_RUN_TRANSITIONS = {
    "created": {"validate_passed": "validated", "validate_failed": "failed"},
}
```

```python
ALLOWED_STEP_TRANSITIONS = {
    "pending": {"step_scheduled": "ready"},
}
```
