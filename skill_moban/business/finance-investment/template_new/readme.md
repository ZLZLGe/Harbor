# Finance-Investment Template

这是面向 `finance-investment` 类 skill 的模板。它综合参考 SkillsMP finance-investment 类热门 skill 的共性能力：组合风险度量、回测与偏差控制、财务建模、投资研究、策略评估、风险阈值监控与可审计报告生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：finance-investment 类 skill 的核心价值，是把金融分析中容易混淆的口径标准化，并把多步骤计算沉淀成可复用 workflow。模板任务应让 skill 在收益、风险、回归、压力测试、阈值判断等环节降低试错成本，而不是替 Agent 提供最终答案。
* **Task目标形态**：任务应要求 Agent 基于真实或冻结的金融数据，产出可审计、可复算、机器可读的投资分析结果。目标形态适合设计成多源数据对齐、指标计算、模型解释、政策阈值判断和结构化报告生成，不适合做静态问答、主观投资建议或单一公式填空。
* **Verifier设计重点**：Verifier 应重算关键金融结果，验证数据口径、单位转换、时间窗口、统计定义和输出结构，而不是绑定某个实现文件。重点应覆盖输入不可变、数值有限、下行风险方向、基准相对指标、因子回归、回测/压力测试参数和风险阈值 breach 的一致性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`finance-investment__arkk-factor-risk-review`
- 类别：`finance-investment`
- 难度：`hard`
- 绑定 Skill：`risk-metrics-calculation`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批冻结市场价格、Fama-French 因子与策略阈值文件，独立重算 ARKK 相对 QQQ 的风险、因子暴露、bootstrap tail risk、stress grid 和 policy breaches。它关注行为结果是否可复算，而不是实现路径是否一致。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 输出 JSON schema、数值类型、有限值和完整 stress grid | 机器可读金融报告与可审计输出 |
| ARKK/QQQ 日收益对齐、累计收益、波动、Sharpe、Sortino、回撤、VaR/CVaR | 组合绩效与下行风险指标 |
| QQQ-relative active return、tracking error、information ratio、beta、downside beta | 基准相对风险与主动风险分析 |
| Fama-French 5 因子加 momentum 回归、RF 对齐、百分比转小数、HAC t-stat | 因子模型、单位口径和稳健统计 |
| moving-block bootstrap 与 deterministic stress harness | 可复现尾部风险与压力测试设计 |
| policy_breaches 与输入文件 hash guardrail | 风险限额监控、输入不可变和反占位输出 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务里，Skill 的核心价值是把风险指标口径、因子回归口径和 deterministic stress grid 标准化；without Skill 仍能算出部分常规指标，但在 Sortino、bootstrap 参数、stress grid 完整性和 policy breach 命名上持续掉分。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均至少在 bootstrap/stress-grid、Sortino 或 policy verifier 上失败；with Skill 三次全通过。 |
| Agent 执行耗时 | `338.0s` | `180.1s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `47%`。 |
| Tokens | `0.282M` | `0.255M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.11x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   └── skills/
├── tests/
├── solution/
└── readme.md
```
