# zheng-agent

Harness-first agent execution system.

## 安装

```bash
pip install -e .[dev]
```

如需使用 OpenAI agent：

```bash
pip install -e .[dev,openai]
```

## 快速开始

```bash
# 使用 mock agent 运行示例任务
zheng-agent run \
  --task-spec examples/demo_task/task_spec.yaml \
  --task-input examples/demo_task/task_input.yaml \
  --agent mock

# 使用 OpenAI agent（需设置 OPENAI_API_KEY）
zheng-agent run \
  --task-spec examples/demo_task/task_spec.yaml \
  --task-input examples/demo_task/task_input.yaml \
  --agent openai
```

## CLI 命令参考

```
zheng-agent run [OPTIONS]

Options:
  -t, --task-spec PATH    TaskSpec YAML 文件路径 [required]
  -i, --task-input PATH   任务输入 YAML/JSON 文件路径 [required]
  -a, --agent CHOICE      Agent 类型 (mock|openai) [default: mock]
  -d, --trace-dir PATH    Trace 输出目录 [default: ./traces]
  -o, --output-format     输出格式 (text|json) [default: text]
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

- **contracts**: 定义合法结构（TaskSpec、AgentDecision、ActionRequest 等）
- **state_machine**: 控制 run/step 状态迁移
- **action_gateway**: 所有外部动作的唯一入口
- **tracing**: append-only 执行事实流
- **evaluation**: 基于 trace 和结果的判定
- **replay**: 从 trace 重建执行语义

核心原则：
- Agent 不能直接调用外部工具，必须通过 Action Gateway
- 所有状态推进必须经过状态机
- 每次 run 都生成完整 trace，并接受 evaluator 判定

## 开发

```bash
# 运行测试
pytest -q

# 安装开发依赖
pip install -e .[dev]
```