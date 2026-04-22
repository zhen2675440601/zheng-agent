# Agent Harness v0.3 Runtime Evolution Plan

## 1. 背景

v0.2 已经完成了 pause/resume、replay CLI、trace 复验链路和 E2E 验证，系统已经具备基础工程闭环：

- 可运行
- 可追踪
- 可复验
- 可通过 CLI 操作

但当前实现仍偏向 demo 级运行时，而不是可承载真实任务的稳定执行系统。主要约束点在于：

- pause/resume 仍带有明显的进程内语义
- 恢复能力对 mock agent 依赖较强
- engine 仍以单 step 模型为主
- action/tool 接入还存在 CLI 内联注册
- replay/evaluator 对 trace payload 结构依赖较松散

因此 v0.3 的目标不是继续增加外围命令，而是把 harness 从“已闭环”推进到“可恢复、可扩展、可演进”的运行时版本。

---

## 2. v0.3 核心目标

v0.3 聚焦四件事：

1. 将 pause/resume 从进程内能力升级为持久化 checkpoint 能力
2. 将 engine 从单 step 扩展为真实多 step 执行模型
3. 为 agent 恢复和 action/tool 接入定义稳定契约
4. 强化 trace/replay/evaluator 的结构化重建能力

这一版不追求并发调度、大规模 provider 扩展或新的高层产品能力，重点是运行时语义稳定。

---

## 3. 推荐实施顺序

1. 先定义 checkpoint / trace / agent recovery contract
2. 再实现 durable pause/resume
3. 再把 engine 改成真实多 step
4. 再收敛 action bootstrap
5. 最后强化 replay/evaluator 和补齐 E2E

原因是：pause/resume、多 step、replay 三者共享同一恢复边界，如果不先收敛契约，后续执行流很容易返工。

---

## 4. 里程碑

### 4.1 定义 durable runtime contract

#### 目标
先收敛恢复与重放边界，再修改执行流，避免实现建立在隐含约定上。

#### 关键文件
- `src/zheng_agent/core/runtime/state_store.py`
- `src/zheng_agent/core/contracts/context.py`
- `src/zheng_agent/core/contracts/action.py`
- `src/zheng_agent/core/tracing/events.py`
- `src/zheng_agent/core/agent/base.py`

#### 具体工作
- 将 `RunState` 从最小暂停状态扩展为 versioned checkpoint snapshot
- checkpoint 至少包含：run/step 状态、step index、trace sequence、agent 恢复元数据、runtime 模式
- 为 trace 的核心事件族明确稳定 payload 结构
- 为 agent 定义恢复接口，避免 runtime 直接操作具体 agent 内部字段
- 为 action request/result 增加更稳定的因果字段与错误分类

#### 现有实现复用
- `RunStateStore.save/load/delete` 继续作为快照落盘入口
- `build_trace_event()` 继续作为统一事件构造入口

---

### 4.2 实现跨进程 pause/resume checkpoint

#### 目标
让暂停和恢复真正依赖磁盘状态，而不是依赖当前 Python 进程中的内存标志。

#### 关键文件
- `src/zheng_agent/core/runtime/engine.py`
- `src/zheng_agent/core/runtime/state_store.py`
- `src/zheng_agent/cli/commands/pause.py`
- `src/zheng_agent/cli/commands/resume.py`

#### 具体工作
- 将 pause 请求统一落到 checkpoint/signal 状态
- 在 engine 的明确检查点保存 checkpoint
- resume 从 persisted snapshot + trace 共同恢复运行上下文
- 在 snapshot 中保存 agent 类型和恢复所需最小元数据
- 让 resume CLI 不再只支持 `mock`

#### 当前缺口
- `resume.py` 仍内联注册 action
- `resume.py` 目前仍带有 “Mock agent may not follow original decision sequence” 警告
- `engine.py` 的 pause 仍以 cooperative/in-memory 语义为主

---

### 4.3 重构 engine 为真实多 step 模型

#### 目标
去掉 `step-1` 的硬编码，让状态机、恢复和 replay 面向真实 step 生命周期。

#### 关键文件
- `src/zheng_agent/core/runtime/engine.py`
- `src/zheng_agent/core/contracts/context.py`
- `src/zheng_agent/core/contracts/decision.py`
- `src/zheng_agent/core/state_machine/transitions.py`

#### 具体工作
- 抽出 step 创建/推进逻辑
- 支持从 persisted step cursor 恢复
- 明确当前 step 完成后如何进入下一 step
- 让 `RunContext.step_index` 成为真实调度状态
- 对 `respond` / `complete` / `fail` 等决策类型做完整执行分支梳理

#### 取舍
- v0.3 先做串行多 step
- 暂不在这一版引入并发 step 调度

---

### 4.4 收敛 action/tool 接入边界

#### 目标
让 action 注册和 runtime bootstrap 从 CLI 命令内联逻辑中抽离，形成统一入口。

#### 关键文件
- `src/zheng_agent/core/action_gateway/registry.py`
- `src/zheng_agent/core/action_gateway/executor.py`
- `src/zheng_agent/cli/commands/run.py`
- `src/zheng_agent/cli/commands/resume.py`

#### 具体工作
- 提供共享的 action bootstrap/catalog
- 统一 fresh run 与 resumed run 的 action 注册来源
- 移除 `run.py` / `resume.py` 中 demo 式内联注册
- 让 action 元信息可以被 trace、replay 和 evaluator 复用

#### 可复用现有分层
- `ActionAdapterRegistry`
- `ActionGatewayExecutor`
- `ActionPolicy`

---

### 4.5 强化 replay / evaluator 的结构化复验

#### 目标
让 replay 不只是“读日志并总结”，而是能够更可信地重建运行语义并复验一致性。

#### 关键文件
- `src/zheng_agent/core/replay/replayer.py`
- `src/zheng_agent/core/evaluation/validators.py`
- `src/zheng_agent/core/tracing/reader.py`
- `src/zheng_agent/core/tracing/events.py`

#### 具体工作
- 让 replay 基于 typed/validated events 做重建
- 保留 step 顺序信息，避免无序汇总影响可解释性
- 为 reevaluate 增加 provenance 信息：trace version、evaluator version、reconstructed final result 来源
- original vs reevaluated 比较时，不只比 `passed/score/reasons`

#### 取舍
- v0.3 先保证稳定重建与可解释比较
- 不追求完全时序模拟器

---

### 4.6 补齐测试与操作文档

#### 目标
确保 v0.3 从 CLI 到 replay 的整链路都可验证，而不是只停留在代码层面。

#### 关键文件
- `tests/runtime/test_pause_resume.py`
- `tests/runtime/`
- `tests/replay/test_replay_cli.py`
- `tests/e2e/test_cli_e2e.py`
- `README.md`
- `CLAUDE.md`

#### 具体工作
- 新增 checkpoint 序列化/反序列化测试
- 新增跨进程 pause/resume 测试
- 新增多 step run 的 runtime 与 replay 测试
- 新增 fresh run 与 resumed run 使用同一 action bootstrap 的 E2E 测试
- 文档补充 v0.3 的恢复语义、限制条件和推荐调试流程

---

## 5. 验证方式

### 合约层
- 为 checkpoint、trace payload、agent recovery metadata 增加序列化/校验测试

### Runtime 层
- 运行中发起 pause，进程结束后重新执行 `resume`，验证 run 可继续完成
- 验证恢复后 step index、sequence、trace 连续性正确

### Multi-step 层
- 构造至少两个 step 的任务
- 验证 step 生命周期、状态迁移和恢复语义

### Replay / Eval 层
- 使用完成态 trace 做重放与 reevaluate
- 比较原始结果与复验结果一致性
- 验证 replay 输出保留 step 顺序和关键恢复依据

### CLI / E2E 层
- `run` → `pause` → 进程退出 → `resume` → `replay --re-evaluate --compare`
- fresh run 与 resumed run 均走同一 action bootstrap

---

## 6. 风险与取舍

- 不把 v0.3 做成并发执行大版本，先专注串行多 step + 可恢复性
- 不急于支持所有 agent provider 的完整恢复，先定义通用 recovery contract，再逐步接入
- 不在 v0.3 引入过多新命令，重点是让现有 run/pause/resume/replay 的语义可靠一致
---

## 7. 完成状态

**v0.3 已完成** (2026-04-22)

### 里程碑完成情况

| 里程碑 | 状态 | 关键提交 |
|--------|------|----------|
| 4.1 Durable runtime contracts | ✅ | f1c4981 |
| 4.2 Cross-process pause/resume | ✅ | f1c4981 |
| 4.3 Multi-step execution | ✅ | 1f536bd |
| 4.4 Action bootstrap | ✅ | c3b85a9 |
| 4.5 Enhanced replay | ✅ | fc8b81e |
| 4.6 Tests & docs | ✅ | 本次提交 |

### 测试覆盖

- **合约层**: `test_v03_contracts.py` (10 tests)
- **Runtime 层**: `test_checkpoint_pause_resume.py` (5 tests), `test_multi_step_execution.py` (7 tests)
- **Action gateway**: `test_bootstrap.py` (13 tests)
- **E2E**: `test_cli_e2e.py` (8 tests)
- **总计**: 91 passed

### 新增文件

- `src/zheng_agent/core/contracts/recovery.py`
- `src/zheng_agent/core/action_gateway/bootstrap.py`
- `tests/contracts/test_v03_contracts.py`
- `tests/runtime/test_checkpoint_pause_resume.py`
- `tests/runtime/test_multi_step_execution.py`
- `tests/action_gateway/test_bootstrap.py`

### 关键变更

- RunState 扩展为 versioned checkpoint (version, step_index, last_event_id, agent_recovery)
- 17 种 typed trace payloads
- Agent recovery protocol (get_recovery_metadata, restore_from_metadata)
- Action causality fields (request_id, error_category, timestamps)
- Cross-process pause via signal file
- Multi-step execution (start_new_step, advance_to_next_step, advance_step decision)
- ActionCatalog and create_registry_for_task()
- ReplayProvenance and reconstruct_run_from_trace()
