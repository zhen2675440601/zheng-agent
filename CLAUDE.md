# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

**v0.1 已完成**。核心模块已实现并通过验收标准验证。

已完成模块：
- contracts (TaskSpec, AgentDecision, ActionRequest/Result, RunResult, EvalResult)
- state_machine (Run/Step 状态迁移表)
- runtime/engine (HarnessEngine 执行引擎)
- action_gateway (executor, registry, policy)
- tracing (JsonlTraceStore, events)
- evaluation (BasicRunEvaluator)
- replay (基础 replayer)
- agent (base protocol, mock agent, OpenAI adapter)
- CLI (run 命令)

设计文档仍在 `docs/specs/`，作为架构基线参考。

## v0.1 验收标准（全部满足）

1. Agent 不能绕过 Action Gateway 访问外部能力 ✅
2. 所有状态推进由状态机控制 ✅
3. 每次 run 生成完整 trace ✅
4. 每次 run 能被 evaluator 判定 ✅
5. 不同 agent adapter 可替换运行 ✅
6. 非法 action/状态迁移会被 harness 拦截 ✅

## Repository rules and hooks

Project Claude hooks are defined in `.claude/settings.json`.

Current project hooks:
- `SessionStart` posts a reminder that this is a design-stage repository and that `CLAUDE.md` plus `docs/specs/` are the source of truth before implementation.
- `PostToolUse` on `Write|Edit` injects lightweight context to keep `docs/specs/` and `CLAUDE.md` aligned when repository-level guidance changes.

Git ignore rules currently include:
- `.claude/settings.local.json` is ignored as a machine-local personal override.

## Common commands

Initialize environment:
```
py -m pip install -e .[dev]
```

Run unit tests:
```
py -m pytest -q
```

Run a single test:
```
py -m pytest tests/runtime/test_engine.py::test_engine_completes_run_with_action -q
```

Run CLI:
```
py -m zheng_agent.cli.main run -t examples/demo_task/task_spec.yaml -i examples/demo_task/task_input.yaml -a mock
```

## Package layout

```
src/zheng_agent/
  core/
    contracts/       # TaskSpec, AgentDecision, ActionRequest/Result, RunResult
    state_machine/   # 状态迁移表
    runtime/         # HarnessEngine
    action_gateway/  # executor, registry, policy
    tracing/         # JsonlTraceStore, events
    evaluation/      # BasicRunEvaluator
    replay/          # replayer
    agent/           # AgentProtocol, mock agent
  agents/llm/        # OpenAI agent adapter
  cli/               # CLI entry point, run command

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
The v0.1 success criterion is verifiability: runs are inspectable, evaluable, and comparable.

## Key domain objects

- `TaskSpec` - 任务静态约束
- `AgentDecision` - agent 结构化决策
- `ActionRequest/ActionResult` - 受控动作请求与返回
- `RunResult` - run 最终产物
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
