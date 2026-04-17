# Agent Harness Design Notes

## 1. 方向收敛结论

本项目不是通用聊天机器人，也不是单纯追求更多工具调用的 Agent 框架。

当前收敛出的方向是：

- 面向企业自动化与实验平台
- 核心是多 Agent 编排，但服从 harness engineering 原则
- 第一版形态偏开发者工具
- 交付形态优先考虑 CLI、Web 控制台、后续云端部署
- 技术路线先以本地开发 MVP 为主，再逐步服务化

### 关键转向

随着需求澄清，项目定位从“可扩展 Agent 框架”进一步修正为：

> 一个按 harness engineering 思路设计的 Agent execution harness。

也就是说，系统中心不再是 Agent 本身，而是：

- contract
- run
- state machine
- action gateway
- trace
- evaluation
- replay

---

## 2. 初始产品定位

一句话定义：

> 一个可编排、可扩展、可观测的多 Agent harness 平台。

后续进一步修正为：

> 一个对 Agent 执行进行约束、控制、观测、验证与回放的工程化运行系统。

---

## 3. 用户与场景

### 目标用户

第一批用户建议聚焦两类：

1. Agent Framework 开发者 / AI Infra 工程师
2. 企业自动化团队

### 核心场景

#### 场景 A：企业任务自动化
- 收集输入
- 路由给不同 Agent
- 调工具执行
- 人工审批
- 输出结果

#### 场景 B：Agent 实验与评测
- 同一任务使用不同 agent strategy 跑
- 比较结果质量、耗时、成本
- 支持回放与回归测试

---

## 4. 关键设计价值

### 原始价值主张
- 易扩展
- 强编排
- 可观测
- 可回放
- 可部署

### Harness-first 修正后的价值主张
- 可控执行
- 可审计
- 可验证
- 可回放
- 可替换

### v0.1 成功标志

从 harness engineering 视角，v0.1 最重要的成功标志是：

> 可验证

也即：同一个 agent 能被标准化测试和对比评估，而不是只能“看起来好像能跑”。

---

## 5. 产品形态

### CLI
适合开发与实验：
- 初始化项目
- 执行 workflow
- 查看 trace
- 回放历史运行
- 查看已注册插件或 action adapter

### Web 控制台
适合观测与调试：
- 查看运行列表
- 查看单次执行时间线
- 查看 step 详情
- 查看 action 调用详情

### 云端部署
作为后续演进方向：
- 托管 runtime
- 接 webhook / queue / API
- 持久化 trace 和状态
- 接权限与审计能力

---

## 6. MVP 演进结论

### 早期 MVP 判断

第一阶段最重要的是证明：

> 开发者能在本地快速定义一个多 Agent workflow，运行它，并清楚看到每一步发生了什么，还能回放一次历史执行。

### 后续基于 harness engineering 的修正

真正的第一阶段验证目标应转为：

1. 每个任务都有明确 contract
2. agent 的所有外部动作都经过受控边界
3. 所有状态推进都经过状态机
4. 每次 run 都能生成可用于验证的 trace
5. 每次 run 都能被 evaluator 判定

---

## 7. 技术路线结论

### 早期技术倾向
- 目标是多语言分层
- 但 v0.1 更适合 Python-first

### 当前推荐

v0.1 推荐：
- Python 作为核心 runtime 与 contract 实现语言
- TypeScript + React 作为 Web trace viewer 技术栈
- SQLite / JSONL 作为本地优先存储

原因：
- 能更快验证 contract、state machine、trace、evaluation 抽象
- 不会过早被跨语言通信和服务化复杂度拖慢

后续可演进到 Go/Python 分层。

---

## 8. 从插件优先到 harness-first 的范式变化

### 之前的中心
- 插件系统
- 编排体验
- 可扩展性

### 现在的中心
- task contract
- action contract
- result contract
- run state machine
- trace
- evaluator

### 关键结论

Agent 不再是“拥有自由工具调用权的智能体”，而是：

> 一个根据 TaskSpec 和历史上下文，产出下一步结构化决策的受控决策器。
