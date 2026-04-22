# zheng-agent

Harness-first agent execution system.

一个按 harness engineering 思路设计的 Agent 执行系统。核心是合约、状态机、动作网关、trace、评估与回放，而非 Agent 本身。

## 特性

- **Contract-first**: 所有执行由明确合约约束
- **状态机控制**: Run/Step 状态迁移显式可追踪
- **Action Gateway**: Agent 不能绕过网关访问外部能力
- **完整 Trace**: 每次 run 生成 append-only 执行事实流
- **可评估**: 每次 run 可被 evaluator 判定
- **Pause/Resume**: 运行中暂停、恢复执行（跨进程可靠）
- **Replay**: 从历史 trace 重放、复验（结构化重建）
- **Multi-step**: 支持多 step 执行模型
- **Typed payloads**: 核心事件有稳定 payload 结构

## 状态

- **v0.1**: 核心闭环完成 (contracts, state machine, engine, gateway, trace, eval)
- **v0.2**: 工程化闭环完成 (pause/resume, replay CLI, 复验链路, E2E tests)
- **v0.3**: 运行时进化完成 (checkpoint, typed payloads, multi-step, action bootstrap, enhanced replay)

```bash
pip install -e .[dev]
```

如需使用 OpenAI agent：

```bash
pip install -e .[dev,openai]
```

## 快速开始

```bash
# 运行测试验证安装
py -m pytest -q

# 使用 mock agent 运行示例任务
py -m zheng_agent.cli.main run \
  -t examples/demo_task/task_spec.yaml \
  -i examples/demo_task/task_input.yaml \
  -a mock

# 交互式对话（mock 模式）
py -m zheng_agent.cli.main chat --mock

# 交互式对话（LLM 模式，需设置 OPENAI_API_KEY）
set OPENAI_API_KEY=sk-xxx
py -m zheng_agent.cli.main chat
```

## CLI 命令

### run - 执行任务

```bash
py -m zheng_agent.cli.main run -t <task_spec.yaml> -i <input.yaml> -a mock -d ./traces
```

选项：
- `-t, --task-spec`: TaskSpec YAML 文件路径 (required)
- `-i, --task-input`: 任务输入 YAML/JSON 文件路径 (required)
- `-a, --agent`: Agent 类型 (mock|openai) [default: mock]
- `-d, --trace-dir`: Trace 输出目录 [default: ./traces]
- `-o, --output-format`: 输出格式 (text|json) [default: text]

### chat - 交互对话

```bash
# Mock 模式（测试流程，无需 API key）
py -m zheng_agent.cli.main chat --mock

# LLM 模式（需要 OPENAI_API_KEY）
py -m zheng_agent.cli.main chat
```

### replay - 分析历史 trace

```bash
# 查看摘要
py -m zheng_agent.cli.main replay <run_id> -d ./traces

# 查看详细事件
py -m zheng_agent.cli.main replay <run_id> -d ./traces -f events

# 重新评估并对比（复验一致性）
py -m zheng_agent.cli.main replay <run_id> -d ./traces \
  -t examples/demo_task/task_spec.yaml \
  --re-evaluate --compare
```

### pause/resume - 暂停恢复

```bash
# 创建暂停信号
py -m zheng_agent.cli.main pause <run_id> -d ./traces

# 恢复执行
py -m zheng_agent.cli.main resume <run_id> -d ./traces
```

## 配置文件格式

### TaskSpec YAML

```yaml
task_type: my_task
title: My Task
description: Task description
input_schema:
  type: object
  properties:
    message:
      type: string
  required:
    - message
output_schema:
  type: object
  required_keys:
    - result
allowed_actions:
  - echo
  - log
max_steps: 10
timeout_seconds: 300
```

### Task Input YAML/JSON

```yaml
message: "Hello"
```

或

```json
{"message": "Hello"}
```

## 架构

本项目采用 harness-first 架构：

| 模块 | 职责 |
|------|------|
| contracts | 定义合法结构（TaskSpec、AgentDecision、ActionRequest 等） |
| state_machine | 控制 run/step 状态迁移 |
| action_gateway | 所有外部动作的唯一入口 |
| tracing | append-only 执行事实流 |
| evaluation | 基于 trace 和结果的判定 |
| replay | 从 trace 重建执行语义、复验 |

核心原则：
- Agent 不能直接调用外部工具，必须通过 Action Gateway
- 所有状态推进必须经过状态机
- 每次 run 都生成完整 trace，并接受 evaluator 判定
- 复验链路保证 replay → evaluator 结果一致

## 开发

```bash
# 运行全部测试
py -m pytest -q

# 运行单个测试
py -m pytest tests/runtime/test_engine.py::test_engine_completes_run_with_action -v

# 运行 E2E 测试
py -m pytest tests/e2e/ -v
```

## 状态

- **v0.1**: 核心闭环完成 (contracts, state machine, engine, gateway, trace, eval)
- **v0.2**: 工程化闭环完成 (pause/resume, replay CLI, 复验链路, E2E tests)

## License

MIT