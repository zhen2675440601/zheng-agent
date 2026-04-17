# Agent Harness v0.1 Contract Definitions

## 1. Task Contract

定义“这次任务允许什么、要产出什么”。

```python
class TaskSpec(BaseModel):
    task_type: str
    title: str
    description: str

    input_schema: dict
    output_schema: dict

    allowed_actions: list[str]
    constraints: dict = {}
    success_criteria: list[str] = []

    max_steps: int = 20
    timeout_seconds: int | None = None
```

### 字段说明
- `task_type`：任务类别，如 `research`, `triage`
- `input_schema`：任务输入结构
- `output_schema`：最终结果结构
- `allowed_actions`：允许调用的动作白名单
- `constraints`：预算、禁区、资源限制
- `success_criteria`：评估依据

---

## 2. Agent Decision Contract

定义 agent 每一步“只能怎么回答”。

```python
DecisionType = Literal[
    "request_action",
    "respond",
    "complete",
    "fail"
]

class AgentDecision(BaseModel):
    decision_type: DecisionType
    reasoning: str | None = None

    action_name: str | None = None
    action_input: dict | None = None

    response: dict | None = None
    final_result: dict | None = None

    failure_reason: str | None = None
```

### 约束
- `request_action` 时必须有 `action_name/action_input`
- `complete` 时必须有 `final_result`
- `fail` 时必须有 `failure_reason`

---

## 3. Action Contract

定义受控动作请求与返回。

```python
class ActionRequest(BaseModel):
    run_id: str
    step_id: str
    action_name: str
    action_input: dict
    requested_by: str
```

```python
ActionStatus = Literal["success", "failed", "rejected"]

class ActionResult(BaseModel):
    status: ActionStatus
    output: dict | None = None
    error: str | None = None
    metadata: dict = {}
```

### 约束
- `action_name` 必须在 `TaskSpec.allowed_actions`
- `rejected` 表示被 harness 拦截，不是执行失败

---

## 4. Result / Eval Contract

定义 run 最终产物和验证结果。

```python
class RunResult(BaseModel):
    run_id: str
    task_type: str
    status: Literal["completed", "failed"]
    output: dict | None = None
    error: str | None = None
```

```python
class EvalResult(BaseModel):
    passed: bool
    score: float | None = None
    reasons: list[str] = []
    metrics: dict = {}
```

---

## 5. 配套上下文 Contract

```python
class RunContext(BaseModel):
    run_id: str
    task_spec: TaskSpec
    task_input: dict
    visible_trace: list[dict] = []
    step_index: int = 0
```

---

## 6. 最小校验规则

1. Task input 必须匹配 `input_schema`
2. Agent 只能输出 `AgentDecision`
3. Action 必须走 `ActionRequest`
4. Final output 必须匹配 `output_schema`
5. Eval 基于 `TaskSpec + Trace + RunResult`
