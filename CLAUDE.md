# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

**v0.2 已完成**。工程化闭环已实现，支持 pause/resume、replay、复验链路。

已完成模块：
- contracts (TaskSpec, AgentDecision, ActionRequest/Result, RunResult, EvalResult)
- state_machine (Run/Step 状态迁移表)
- runtime/engine (HarnessEngine 执行引擎 + pause/resume)
- runtime/state_store (RunState 持久化)
- action_gateway (executor, registry, policy)
- tracing (JsonlTraceStore, events)
- evaluation (BasicRunEvaluator)
- replay (replayer + reevaluate_trace + compare)
- agent (base protocol, mock agent, OpenAI adapter, ChatAgent)
- CLI (run, chat, pause, resume, replay 命令)

设计文档仍在 `docs/specs/`，作为架构基线参考。

## v0.1 验收标准（全部满足）

1. Agent 不能绕过 Action Gateway 访问外部能力 ✅
2. 所有状态推进由状态机控制 ✅
3. 每次 run 生成完整 trace ✅
4. 每次 run 能被 evaluator 判定 ✅
5. 不同 agent adapter 可替换运行 ✅
6. 非法 action/状态迁移会被 harness 拦截 ✅

## v0.2 新增能力

- **pause/resume**: 运行中暂停、恢复执行
- **replay CLI**: 查看历史 trace、重新评估
- **复验链路**: trace → replay → evaluator 结果一致性验证
- **chat 命令**: 交互式对话（LLM 或 mock）

## Repository rules and hooks

Project Claude hooks are defined in `.claude/settings.json`.

Current project hooks:
- `SessionStart` posts a reminder that this is a design-stage repository and that `CLAUDE.md` plus `docs/specs/` are the source of truth before implementation.
- `PostToolUse` on `Write|Edit` injects lightweight context to keep `docs/specs/` and `CLAUDE.md` aligned when repository-level guidance changes.

Git ignore rules currently include:
- `.claude/settings.local.json` is ignored as a machine-local personal override.

## Quick Start

```bash
# 安装
git clone https://github.com/zhen2675440601/zheng-agent.git
cd zheng-agent
py -m pip install -e .[dev]

# 运行测试
py -m pytest -q

# 运行示例任务
py -m zheng_agent.cli.main run -t examples/demo_task/task_spec.yaml -i examples/demo_task/task_input.yaml -a mock

# 交互式对话
py -m zheng_agent.cli.main chat --mock
```

## CLI Commands

### run - 执行任务
```bash
py -m zheng_agent.cli.main run -t <task_spec.yaml> -i <input.yaml> -a mock -d ./traces
```

### chat - 交互对话
```bash
# 使用 mock（测试流程）
py -m zheng_agent.cli.main chat --mock

# 使用 LLM（需要 OPENAI_API_KEY）
set OPENAI_API_KEY=sk-xxx
py -m zheng_agent.cli.main chat
```

### replay - 分析历史 trace
```bash
# 查看摘要
py -m zheng_agent.cli.main replay <run_id> -d ./traces

# 查看详细事件
py -m zheng_agent.cli.main replay <run_id> -d ./traces -f events

# 重新评估并对比
py -m zheng_agent.cli.main replay <run_id> -d ./traces -t task_spec.yaml --re-evaluate --compare
```

### pause/resume - 暂停恢复
```bash
# 创建暂停信号
py -m zheng_agent.cli.main pause <run_id> -d ./traces

# 恢复执行
py -m zheng_agent.cli.main resume <run_id> -d ./traces
```

## Package layout

```
src/zheng_agent/
  core/
    contracts/       # TaskSpec, AgentDecision, ActionRequest/Result, RunResult
    state_machine/   # 状态迁移表
    runtime/
      engine.py      # HarnessEngine
      state_store.py # RunState 持久化
    action_gateway/  # executor, registry, policy
    tracing/         # JsonlTraceStore, events
    evaluation/      # BasicRunEvaluator
    replay/          # replayer, reevaluate_trace, compare
    agent/           # AgentProtocol, mock agent
  agents/
    llm/             # OpenAI agent adapter
    chat_agent.py    # ChatAgent
  cli/               # CLI entry point, run/chat/pause/resume/replay

tests/
  contracts/         # 合约测试
  state_machine/     # 状态机测试
  runtime/           # engine + pause/resume 测试
  replay/            # replay + 复验测试
  e2e/               # CLI 端到端测试
```

## Architecture overview

The project is a harness-first agent execution system. The core system revolves around:
- contracts
- run lifecycle
- state machine
- action gateway
- trace
- evaluation
- replay

### Core design principles

#### Contract-first
All execution is governed by explicit contracts:
- Task Contract
- Agent Decision Contract
- Action Contract
- Result Contract
- Eval Contract

#### Controlled execution boundaries
Two boundaries are first-class:
- tools/actions are invoked only through an Action Gateway
- run and step progression go through an explicit state machine

#### Verifiability over convenience
The success criterion is verifiability: runs are inspectable, evaluable, replayable, and comparable.

## Key domain objects

- `TaskSpec` - 任务静态约束
- `AgentDecision` - agent 结构化决策
- `ActionRequest/ActionResult` - 受控动作请求与返回
- `RunResult` - run 最终产物
- `RunState` - 运行状态持久化（用于 pause/resume）
- `EvalResult` - 执行验证结果

## State model

Run states: created, validated, ready, running, waiting_action, paused, completed, failed, cancelled

Step states: pending, ready, running, waiting_action, completed, failed

State transitions are event-driven and explicit via `apply_run_event/apply_step_event`.

## Implementation guidance

1. Preserve the harness-first model
2. Treat Action Gateway mediation as mandatory for external actions
3. Keep trace and evaluation as first-class runtime outputs
4. Validate input/output against schemas
5. Support pause/resume for debugging
6. Ensure replay → evaluator consistency
