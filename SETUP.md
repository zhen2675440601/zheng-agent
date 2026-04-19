# 新环境设置指南

本文档说明在另一台电脑上拉取项目并使用 Claude Code 时需要注意的事项。

---

## 1. 环境要求

- **Python**: 3.12+
- **Claude Code**: 最新版本
- **Git**: 任意版本

---

## 2. 拉取项目后的首次设置

```bash
# 拉取项目
git clone https://github.com/zhen2675440601/zheng-agent.git
cd zheng-agent

# 安装开发依赖
pip install -e .[dev]

# 验证安装成功
pytest -q
zheng-agent --help
```

---

## 3. Claude Code 相关配置

### 3.1 项目规则位置

项目级 Claude Code 规则在 `CLAUDE.md` 中定义，包括：
- 仓库当前状态（设计阶段 vs 实现阶段）
- 架构概述和核心原则
- 依赖方向约束
- 状态模型
- 实现优先级

Claude Code 会在每次会话开始时自动读取 `CLAUDE.md`。

### 3.2 文档语言约定

**所有项目文档必须使用中文书写。**

这条规则已记录在：
- `CLAUDE.md` 的 "Documentation language rule" 部分
- Claude Code memory 中

如果你发现 Claude Code 输出了英文文档，提醒它："所有文档用中文书写"。

### 3.3 设计文档是 Source of Truth

当前项目仍处于从设计进入实现的过渡阶段。核心设计文档位于：

```
docs/specs/
├── agent-harness-design-notes.md
├── agent-harness-v0.1-harness-first-architecture.md
├── agent-harness-v0.1-contract-definitions.md
└── agent-harness-v0.1-state-machine.md
```

实现计划位于：

```
docs/superpowers/
├── specs/2026-04-18-v0.1-implementation-ready-design.md
└── plans/2026-04-18-v0.1-core-harness-first-implementation.md
```

如果 Claude Code 在实现过程中有疑问，应优先参考这些文档，而不是凭推断行事。

---

## 4. 架构核心原则

向 Claude Code 提问或请求实现时，应提醒它遵循以下原则：

### Harness-First

项目不是通用 agent 框架，而是 **对 Agent 执行进行约束、控制、观测、验证与回放的工程化运行系统**。

Agent 在系统里只是一个受控决策器。系统真正的中心是：
- Contract
- Run
- State Machine
- Action Gateway
- Trace
- Evaluation

### Contract-First

所有执行必须先满足契约：
- Task Contract
- Agent Decision Contract
- Action Contract
- Result Contract
- Eval Contract

### 强约束边界

两条边界不可绕过：
1. **工具边界**: Agent 不直接调用外部工具，只能提交 ActionRequest，由 Action Gateway 执行
2. **状态边界**: 所有执行推进都必须经过状态机

---

## 5. 常用命令

| 命令 | 说明 |
|------|------|
| `pytest -q` | 运行全部测试 |
| `zheng-agent --help` | 查看 CLI 帮助 |
| `zheng-agent run -t ... -i ... -a mock` | 运行示例任务 |

---

## 6. 依赖方向约束

实现时应保持单向依赖：

```
runtime -> contracts, state_machine, action_gateway, tracing
action_gateway -> contracts
evaluation -> contracts, tracing
replay -> tracing, runtime, contracts
agent -> contracts
```

**禁止反向依赖**：
- contracts 不应依赖执行模块
- tracing 不应依赖具体 agent 实现
- agent 不应依赖 runtime 内部状态

---

## 7. 当前实现状态

已完成：
- ✅ 核心库骨架（contracts、state_machine、tracing、action_gateway、runtime、evaluation、replay）
- ✅ CLI 入口 (`zheng-agent run`)
- ✅ OpenAI Agent Adapter
- ✅ 示例配置和 README

待做：
- ⏳ 真实 LLM agent 测试（需要 API key）
- ⏳ 更丰富的 action adapters
- ⏳ Web trace viewer
- ⏳ 更多示例场景

---

## 8. Memory 文件

Claude Code 的持久记忆位于：

```
~/.claude/projects/<project-path>/memory/
├── MEMORY.md          # 索引文件
└── documentation_language_chinese.md  # 文档语言偏好
```

如果切换电脑后 Claude Code 不知道文档语言偏好，可以让它读取 memory 目录，或直接提醒："所有文档用中文书写"。

---

## 9. 遇到问题时的排查顺序

1. 先读 `CLAUDE.md` 了解当前状态
2. 读 `docs/specs/` 了解架构基线
3. 读 `README.md` 了解使用方法
4. 运行 `pytest -q` 验证环境
5. 如果测试失败，检查 Python 版本和依赖安装