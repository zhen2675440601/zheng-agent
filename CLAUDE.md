# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

**v0.5 已完成**。provider-grade parity + release hardening。

已完成模块：
- contracts (TaskSpec, AgentDecision, ActionRequest/Result, RunResult, EvalResult, recovery metadata + RecoveryError)
- state_machine (Run/Step 状态迁移表)
- runtime/engine (HarnessEngine 执行引擎 + multi-step + checkpoint + guardrails)
- runtime/state_store (RunState versioned checkpoint snapshot)
- action_gateway (executor, registry, policy, bootstrap catalog)
- tracing (JsonlTraceStore, events, typed payloads)
- evaluation (BasicRunEvaluator with status-aware failure detection)
- replay (replayer + reconstruct_run_from_trace + compare + provenance)
- agent (base protocol with recovery, mock agent, OpenAI adapter with test boundary, ChatAgent)
- CLI (run, chat, pause, resume, replay 命令 + unified bootstrap)

设计文档在 `docs/specs/`，v0.3 实施计划见 `docs/specs/agent-harness-v0.3-runtime-evolution-plan.md`。

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

## v0.3 新增能力（已完成）

- **Durable checkpoint**: RunState 扩展为 versioned checkpoint snapshot
- **Typed trace payloads**: 核心事件族有稳定 payload 结构（17 种 typed payloads）
- **Agent recovery protocol**: agent 可通过 metadata 恢复位置
- **Cross-process pause**: 通过信号文件实现跨进程暂停
- **Multi-step execution**: 支持多 step 执行模型，advance_step/respond decision
- **Checkpoint boundaries**: step start、action before/after 保存 checkpoint
- **Action causality**: request_id、error_category、timestamps 字段
- **Action bootstrap**: 统一的 ActionCatalog 和 create_registry_for_task()
- **Enhanced replay**: reconstruct_run_from_trace()、provenance tracking、step ordering preservation

## v0.4 新增能力（已完成）

- **Runtime guardrails**: `max_steps` / `timeout_seconds` 已在 engine 中强制执行
- **Decision contract**: LLM parser / prompt 已支持 `advance_step`、`respond` 等完整决策类型
- **Lifecycle-true resume**: mock resume 基于 checkpoint 中序列化决策恢复，resume 不再走简化 complete fallback
- **CLI bootstrap**: `run` / `chat` / `resume` 已复用共享 runtime bootstrap；CLI version 改为从包版本导出
- **Testing**: runtime / parser / CLI 基础验证已补齐

## v0.5 新增能力（已完成）

- **Recovery contract hardening**: `AgentRecoveryMetadata.validate_for_restore()` 校验必需字段，`RecoveryError` 统一恢复失败处理
- **OpenAI test boundary**: `OpenAIAgent.set_client_for_testing()` 支持无网络测试
- **Provider parity tests**: mock/openai 恢复矩阵测试覆盖 checkpoint kinds、trace 连续性、恢复验证
- **Release hygiene**: 版本号统一为 `0.5.0`（CLI、pyproject、包导出），README/CLAUDE 同步


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
