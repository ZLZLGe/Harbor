# 🛠️ Debugging 任务模板规范与设计指南

本规范定义了 Agent（如 Codex）在设计和生成 `debugging` 类任务时的核心标准。与常规的“从零开发”任务不同，Debugging 任务的核心在于：

**给定残缺或性能退化的系统 -> 使用特定探针诊断 -> 在严格约束下修复 -> 验证修复且不引发回归（Regression）**

## 🎯 Agent 设计 Debugging 任务的核心范式

当 Agent 参考本模板造任务时，必须严格遵循以下四大核心要点：

### 1. 症状导向与约束逆向构建（Symptom-Driven Constraints）

任务说明 `instruction.md` 严禁直接暴露问题根因或指导修复逻辑。只能向 Solver 提供“表现层症状”、业务边界约束以及禁止事项，迫使模型进行真实的推理与排障。


### 2. 探针型技能注入（Probe-Oriented Skill Integration）

绑定的 Skill 不再是代码生成辅助，而是作为诊断仪器。必须设计特定的测量探针，例如测速脚本、日志分析器、压测工具，帮助 Solver 复现问题并精准度量修复前后的指标变化。

### 3. 高仿真靶场与防作弊拦截（High-Fidelity & Anti-Cheat Guardrails）

必须摒弃纯净沙盒，构建包含真实上下游依赖的故障现场。Verifier 需强制断言运行时经过真实的下游链路，拦截诸如篡改测试桩、删除数据节点、降级动态组件等“伪修复（Hack-fix）”捷径。

### 4. 引入量化与长时序测试（Quantitative & Soak Testing）

判定标准不能停留在简单的 Pass/Fail。需要引入长会话交互链路测试（Soak Testing）以捕获内存或事件泄漏，并依赖量化指标，例如 CLS 阈值、JS 瀑布流耗时，来验证修复效果。

## 🌟 标准示例任务：`nextjs-analytics-dashboard-runtime-regression-debugging`

以下任务是本模板范式的标准实现，展示了如何将上述设计理念落地。

## 📌 任务元数据

- 任务名称：`nextjs-analytics-dashboard-runtime-regression-debugging`
- 类别：`debugging`
- 难度：`hard`
- 状态：✅ `APPROVE`
- 标签：`react`, `nextjs`, `browser-testing`, `hydration`, `cls`, `lazy-loading`, `interaction-latency`, `dashboard`

任务描述：

修复 Next.js Analytics Dashboard 的前端运行时回归问题。核心解决：Deep-link 冷启动不稳定且 linked alert context 错位、Advanced Insights 提前加载、以及长会话交互退化。

配套技能（Skills）- 探针型工具：

- `browser-testing`：统一的浏览器复现与测量方法。
- `measure-dashboard-waterfall.ts`：测量首页加载及 Advanced Insights 的 JS Waterfall。
- `measure-dashboard-deeplink.ts`：复现 Deep-link 冷启动、Filter 漂移、linked context 错位与 CLS。
- `measure-dashboard-soak.ts`：执行长会话交互序列，排查 Listener 泄漏、脉冲 Fan-out 与刷新延迟。

## 📊 验证与测试指标（Oracle & Verifier）

- 整体结论：✅ 通过（Reward: `1`）
- 测试用例：`9/9` 通过

Verifier 策略：

- 主测：Deep-link 稳定性、按需加载机制、长会话运行时稳定性。
- 防作弊：拦截篡改隐藏服务、替换真实数据、移除关键 `data-testid` 等伪修复行为。

多模态：

- 不适用（纯前端 / 浏览器运行时任务）。

## ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值不是单纯提速，而是把浏览器探针、deeplink 量测和 soak 复现路径标准化，强迫 agent 真的碰到冷启动 deeplink 的 CLS 回归与抽屉上下文约束；没有 Skill 时，agent 虽然更快结束，但会稳定停在“表面看起来差不多、task-level 仍不过”的错误解。

基于最近 `3` 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近三次有效对照里，With Skill 连续 3 次 task-level 全通过；Without Skill 连续 3 次都未能通过 |
| 总耗时 | `1332.2s` | `1682.7s` | With Skill 更慢，但换来稳定通过；Without Skill 更快结束却稳定停在错误解 |
| Input Tokens | `0.69M` | `1.91M` | With Skill 会显著增加诊断上下文与验证开销，平均输入 token 约为 Without Skill 的 `2.78x` |



## 📁 标准目录结构说明

```text
.
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动网站与隐藏下游服务
│   ├── website/            # 待修复的应用源码（故障现场）
│   ├── api-simulator/      # 提供真实下游数据和依赖的隐藏服务/模拟后端（防作弊靶场）
│   └── skills/             # 任务绑定的诊断 Skill 定义与配套探针脚本
├── tests/                  # Verifier 与 Guardrail 测试集（量化与时序测试）
└── solution/               # 官方参考修复代码及 solve.sh
```
