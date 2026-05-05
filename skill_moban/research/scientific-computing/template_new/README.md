# Scientific Computing Data Analysis Template

这是面向 scientific-computing 类 skill 的模板。它综合参考 SkillsMP Scientific Computing 类热门 skill 的共性能力：多源科学数据读取、SQL/pandas 数据清洗、统计趋势检验、可解释归因建模、质量控制和可复现实验交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：Scientific Computing 类热门 skill 的共同价值，是把复杂科学数据从“能读文件”推进到“能解释、能复核、能稳定复现”的分析链路。它们通常覆盖数据结构识别、领域变量清洗、统计建模、质量控制和机器可读报告，使 agent 不只修表面格式，而是按科学分析工作流完成交付。
* **Task 目标形态**：任务应提供真实风格的多源数据链路，例如数据库、仪器观测、元数据、事件窗口和下游 schema，而不是静态 toy CSV。目标输出应包含主结果、诊断摘要和 workflow audit，迫使 solver 同时完成 SQL 抽取、pandas 转换、统计分析和解释性报告。
* **Verifier 设计重点**：Verifier 需要同时检查输出契约、数据链路、统计合理性和防作弊约束。对于科学计算任务，不宜只卡唯一数值答案，而应动态重算关键 oracle、验证质量控制和模型输出范围，并检查 solver 是否留下足够的 SQL/pandas/统计工作流证据。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`scientific-computing__lake-observatory-qc-attribution`
- 类别：Scientific Computing
- 难度：`hard`
- 绑定 Skill：`data-analyst`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法从 SQLite 和 CSV 原始输入重建完整湖泊观测分析链路，完成去重、单位换算、QC/event-window 过滤、日尺度聚合、鲁棒趋势、驱动因子归因和 workflow audit。E2B oracle `lake-observatory-oracle-e2b-20260429-010944` 已通过，Reward 为 `1.0`。
- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 必需 CSV/JSON 输出存在、字段顺序和类型可解析 | 结构化数据分析交付 |
| 从 SQLite/CSV 动态复算站点、raw rows、日期范围和 QC 统计 | SQL 数据抽取、数据库设计理解、pandas 清洗 |
| 检查站点趋势使用鲁棒/非参数方法且斜率、p-value、缺失率处于合理范围 | 时间序列分析、假设检验、异常值处理 |
| 检查 Heat/Flow/Wind/Human 四类归因、贡献率归一化、rank 与 summary 一致 | 相关性分析、基础预测建模、解释性归因 |
| 检查 `analysis_workflow_audit.json` 中 SQL、pandas、统计、性能、示例结果和解释性证据 | skill 输出格式：注释、示例结果、性能考虑、发现解释 |
| 防硬编码、禁复制输入数据、禁外部账号/云服务、重复运行确定性，并确认绑定 skill 原样安装 | 防作弊、可复现性、skill 绑定与安全边界 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 SQLite 抽取、pandas 清洗、鲁棒趋势检验、归因建模和 workflow audit 标准化；新增的 audit 输出专门验证 solver 是否内化了 SQL/pandas/statistics 工作流，而不是只凑 CSV 字段。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | Without Skill 均未通过，主要因为剥离 `environment/skills/` 后缺少绑定 `data-analyst` skill，并更容易遗漏 skill 输出格式 audit；With Skill 三次均形成完整 SQL/pandas/统计交付链路 |
| Agent 执行耗时 | `644.0s` | `596.1s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `7.4%` |
| Tokens | `939.0K` | `778.6K` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.21x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── generate_seed_data.py
│   └── skills/
│       └── data-analyst/
│           └── SKILL.md
├── tests/
│   ├── reference_metrics.py
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed_run_analysis.py
    └── solve.sh
```
