Data Analysis Template

这是面向 Data Analysis 类 skill 的模板。它综合参考 SkillsMP Data Analysis 类热门 skill 的共性能力：从原始表格、事件流、业务指标、统计模型和可视化输出中提取可审计结论，并把分析过程沉淀为可运行、可验证、可复现的数据交付链路。

## 第一部分：任务设计参考

* **Skill 价值定位**：Data Analysis 类 skill 的收益应体现在把杂乱数据转成可信业务结论，而不是替用户猜一个静态答案。它通常需要覆盖数据读取、清洗、去重、聚合、统计校正、指标解释、图表/报告一致性和业务语义复核。高质量任务应让 skill 帮助 Agent 更快建立分析口径、定位混杂因素，并避免只修表层输出。

* **Task目标形态**：任务应要求 Agent 面对真实风格的数据包和业务约束，修复或重建一条可运行的数据分析链路。输出应是可审计的 CSV/TSV/JSON/图表长表或报告摘要，并能从原始数据追溯到最终结论。不应设计成 puzzle、单文件格式转换、复制预期答案或只靠隐藏 oracle 的静态比对。

* **Verifier设计重点**：Verifier 应关注分析行为结果，包括关键指标是否从原始数据正确推导、清洗/去重/窗口/统计口径是否合理、多个交付物之间是否一致。它还应包含防作弊测试，拦截硬编码结论、跳过真实链路、伪造下游服务、未控制混杂因素或图表与明细脱节的解法。验证不应绑定唯一实现，但必须能区分完整分析链路和看似合理的 naive 输出。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`data-analysis__promo-roi-stockout-audit`
- 类别：Data Analysis
- 难度：`hard`
- 绑定 Skill：`data-analyst`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法重建完整促销分析链路，从原始 POS、库存、天气、客流和促销合同动态生成全部交付物，并调用本地 `promo-enrichment` 服务写入真实注释。E2B oracle `promo-roi-oracle-e2b-20260426-13` 已通过，Reward 为 `1.0`。

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 必需输出文件、字段和 JSON 顶层键可解析 | 输出契约理解与结构化交付 |
| 从原始 POS 重算净收入、净销量、毛利和业务日期 | 数据清洗、最新状态去重、本地时区处理 |
| 从库存快照区间重算促销窗口缺货暴露小时 | 时间区间裁剪与事件序列分析 |
| 检查品类 uplift、诊断表和绘图长表一致性 | 统计口径、表间一致性、可视化数据治理 |
| 检查门店风险审计与风险图表一致性 | KPI 审计、异常识别、风险分层 |
| 检查 enrichment 服务和模型摘要 | 真实下游链路调用、可追溯报告说明 |
| 防 naive UTC、重复订单、未校正 uplift 和伪造报告 | 防作弊与行为级验证 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把原始事件分析工作流标准化：先读合同和输出契约，再做 POS 最新状态去重、本地业务日、缺货区间裁剪、校正基线、真实 enrichment 调用和表间一致性检查。Without Skill 也理论上可解，但更容易停在“指标看起来合理”的半成品，遗漏双口径诊断、模型说明或风险审计细节。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | Without Skill 均至少保留一项 verifier 失败，主要集中在未校正/校正口径说明、风险等级分层和 diagnostics 可追溯字段 |
| Agent 执行耗时 | `749.8s` | `429.7s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `42.7%` |
| Tokens | `76.5K` | `49.3K` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.55x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── pipeline/
│   ├── services/
│   ├── skills/
│   └── vendor/
├── tests/
│   ├── reference_metrics.py
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed_run_analysis.py
    └── solve.sh
```
