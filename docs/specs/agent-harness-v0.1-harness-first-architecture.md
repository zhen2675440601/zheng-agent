# Agent Harness v0.1 Harness-First Architecture Spec

## 1. 产品定义

Agent Harness v0.1 不是一个“方便拼 Agent 的框架”，而是一个：

> 对 Agent 执行进行约束、控制、观测、验证与回放的工程化运行系统。

Agent 在系统里只是一个受控决策器。
系统真正的中心是：

- Contract
- Run
- State Machine
- Action Gateway
- Trace
- Evaluation

---

## 2. v0.1 第一原则

### Contract-first
任何执行都必须先满足契约：

- Task Contract
- Agent Decision Contract
- Action Contract
- Result Contract
- Eval Contract

### 强约束边界

v0.1 先强约束两条边界：

1. 工具边界  
   Agent 不直接调用外部工具，只能提交 ActionRequest
2. 状态边界  
   所有执行推进都必须经过状态机

---

## 3. 核心对象模型

### 3.1 TaskSpec
定义任务的静态约束。

建议字段：
- `task_type`
- `input_schema`
- `output_schema`
- `allowed_actions`
- `success_criteria`
- `constraints`

作用：
- 定义这个任务允许 agent 做什么
- 定义什么叫完成

### 3.2 Run
一次任务执行实例。

建议字段：
- `run_id`
- `task_spec_id`
- `status`
- `input`
- `context`
- `current_step`
- `final_result`
- `eval_result`

### 3.3 StepAttempt
某个步骤的一次尝试。

建议字段：
- `step_id`
- `attempt_id`
- `status`
- `agent_decision`
- `action_request`
- `action_result`

### 3.4 AgentDecision
Agent 产出的结构化决策，而不是自由文本。

建议支持三类基础决策：
- `request_action`
- `respond`
- `complete`
- `fail`

### 3.5 ActionRequest
Agent 请求 harness 执行一个外部动作。

建议字段：
- `action_name`
- `action_input`
- `requested_by`
- `step_id`

### 3.6 ActionResult
Action Gateway 返回的结构化结果。

建议字段：
- `status`
- `output`
- `error`
- `metadata`

### 3.7 EvalResult
执行验证结果。

建议字段：
- `passed`
- `score`
- `reasons`
- `metrics`

---

## 4. 状态机规格

### 4.1 Run 状态
建议 v0.1 固定为：

- `created`
- `validated`
- `ready`
- `running`
- `waiting_action`
- `paused`
- `completed`
- `failed`
- `cancelled`

### 4.2 Step 状态
建议：

- `pending`
- `ready`
- `running`
- `waiting_action`
- `completed`
- `failed`

### 原则
- 所有状态变化必须由 harness 事件驱动
- Agent 不能直接写 run 状态
- Step 的进入/退出必须被 trace 记录

---

## 5. Agent Contract

Agent 在 v0.1 里应被定义为：

> 根据 TaskSpec、当前上下文和历史事件，返回一个结构化决策的组件。

### Agent 输入
- `task_spec`
- `run_context`
- `step_context`
- `visible_trace`
- `allowed_actions`

### Agent 输出
只能是以下之一：
1. 请求动作
2. 给出中间响应
3. 声明完成
4. 声明失败

### 明确禁止
- 直接调用 tool
- 直接改状态
- 直接写外部存储
- 直接绕过 harness 输出最终结果

---

## 6. Action Gateway 规格

Action Gateway 是所有外部动作的唯一入口，负责：

- 校验 action 是否被允许
- 校验输入 schema
- 执行动作
- 记录动作事件
- 返回标准 ActionResult

### Gateway 流程
1. 接收 `ActionRequest`
2. 检查是否在 `TaskSpec.allowed_actions`
3. 检查输入是否合法
4. 调用具体 action adapter
5. 生成 `ActionResult`
6. 写入 trace
7. 推动状态机继续执行

---

## 7. Trace 规格

Trace 不是日志，而是执行事实记录。

### 必须记录的事件
- `run_created`
- `run_validated`
- `run_started`
- `step_started`
- `agent_decision_produced`
- `action_requested`
- `action_approved`
- `action_executed`
- `action_failed`
- `step_completed`
- `step_failed`
- `run_completed`
- `run_failed`
- `evaluation_completed`

### 每条事件最少字段
- `event_id`
- `run_id`
- `step_id`
- `event_type`
- `timestamp`
- `payload`

---

## 8. Eval 接口规格

既然 v0.1 的成功标志是可验证，evaluation 必须是一等公民。

### Evaluator 接口
```python
class RunEvaluator:
    def evaluate(self, task_spec, run_trace, final_result) -> EvalResult:
        ...
```

### v0.1 评估目标
至少支持：
- pass / fail
- 规则原因
- 可选数值评分

### 验证维度
- 是否完成任务目标
- 是否使用了非法 action
- 是否违反状态迁移规则
- 输出是否满足 output schema

---

## 9. Replay 规格

Replay 是为了复盘和验证。

### 支持能力
- replay 整个 run
- replay 单个 step

### 但必须保证
- 决策路径可还原
- 失败点可定位
- 验证结果可重跑

---

## 10. 模块边界

建议模块组织：

```text
core/
  contracts/
    task.py
    decision.py
    action.py
    result.py
    evaluation.py

  state_machine/
    run_state.py
    step_state.py
    transitions.py

  runtime/
    engine.py
    dispatcher.py
    context.py

  action_gateway/
    executor.py
    registry.py
    policy.py

  tracing/
    events.py
    store.py
    reader.py

  evaluation/
    base.py
    validators.py

  replay/
    replayer.py

  agent/
    base.py
    adapter.py
```

---

## 11. 依赖方向

必须保持单向依赖：

```text
runtime -> contracts
runtime -> state_machine
runtime -> action_gateway
runtime -> tracing

action_gateway -> contracts
evaluation -> contracts + tracing
replay -> tracing + runtime + contracts
agent -> contracts
```

### 明确禁止
- agent 依赖 runtime 内部状态实现
- tracing 依赖具体 agent
- evaluation 依赖具体 action adapter
- contracts 依赖任何执行模块

---

## 12. v0.1 最小可交付物

必须交付这 6 项：

1. Task Contract
2. Agent Decision Contract
3. Action Gateway
4. Run / Step State Machine
5. Trace Event Store
6. Run Evaluator

---

## 13. v0.1 验收标准

只有同时满足下面几点，才算 v0.1 成功：

1. Agent 不能绕过 Action Gateway 访问外部能力
2. 所有状态推进都由状态机控制
3. 每次 run 都生成完整 trace
4. 每次 run 都能被 evaluator 判定
5. 不同 agent adapter 可在同一 contract 下替换运行
6. 非法 action / 非法状态迁移会被 harness 拦截
