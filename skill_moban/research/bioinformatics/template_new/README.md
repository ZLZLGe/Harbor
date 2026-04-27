# Bioinformatics Template

这是面向 `bioinformatics` 类 skill 的模板。它综合参考 SkillsMP bioinformatics 类热门 skill 的共性能力：转录组分析、bulk RNA-seq 差异表达、批次/混杂因素校正、设计矩阵与 contrast 管理、基因面板审计、功能注释和可复现结果包生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：bioinformatics 类 skill 的核心价值，是把复杂生物数据分析中的统计建模、样本注释、对比方向、混杂校正和下游解释流程标准化。模板任务应让 skill 在 count-aware modeling、design validation、contrast handling、panel audit 和结果包一致性上降低诊断成本，而不是给出固定基因列表或隐藏答案。
* **Task目标形态**：任务应要求 Agent 基于真实或真实风格的组学数据，修复或重建可复现分析链路，并产出可被审计的多文件结果包。目标形态适合设计成 RNA-seq DE 修复、批次效应诊断、单细胞/多组学 QC、基因面板复核、注释服务联动和 report.json 汇总，不适合做静态表格填空、手写结论或跳过统计流程的伪分析。
* **Verifier设计重点**：Verifier 应从原始 counts、metadata 和配置动态重跑 reference 分析，验证输出行为是否与统计模型和生物学合同一致。重点应覆盖输出 schema、样本/基因对齐、显著性集合、baseline vs corrected model、panel diagnostic status、report/table 一致性、下游注释链路和防复制 broken outputs。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`bioinformatics__pasilla-batch-aware-de-repair`
- 类别：`bioinformatics`
- 难度：`hard`
- 绑定 Skill：`pydeseq2`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批 `pasilla` raw counts、sample metadata、priority panel、analysis config 和本地 `panel-annotation` 服务，独立重跑 baseline 与 corrected PyDESeq2 分析。它关注正式交付物是否反映 `~type + condition` 的校正模型，并保留 `~condition` 基线模型的面板审计证据。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 五类输出存在并可解析：DE results、significant genes、normalized counts、panel diagnostics、report | 可复现 RNA-seq 结果包与文件合同 |
| `9921` 个过滤后基因、列结构、样本对齐、normalized counts 覆盖 | count matrix 过滤、样本元数据对齐和输出 schema |
| 动态重跑 PyDESeq2 corrected/baseline reference | 设计公式、contrast、负二项模型和多重检验 |
| `stable_treatment_signal`、`rescued_after_adjustment`、`nuisance_sensitive_drop` 分类 | 混杂因素校正、panel 诊断和生物学解释 |
| `report.json` 与表格之间的 counts、方向、panel summary、diagnostic summary 一致 | 机器可读报告和跨文件一致性 |
| 与 `broken_outputs/` 显著不同，且 corrected formula 包含 `type` 与 `condition` | 防复制错误交付物、反静态结果和正式模型约束 |

### ⚡ Skill 相关性评估

结论：强相关，但存在可解释的小幅波动。这个任务里，Skill 的核心价值是把 PyDESeq2 的 corrected/baseline 双模型诊断流程、panel 审计框架，以及最终 `report.json` / `significant_genes.tsv` 的精确 schema 明确化，从而显著降低诊断和收敛成本。

基于最近 **3** 次有效对照实验（均基于同一任务版本与同类 E2B 运行口径；with/without 的唯一区别只来自 `environment/skills/`）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | With Skill 已出现稳定通过案例；Without Skill 仍未通过。 |
| Agent 执行耗时 | `408.2s` | `326.3s` | With Skill 的定位与收敛更快，平均 Agent 耗时降低约 `20.1%`。 |
| Tokens | `0.90M` | `0.98M` | With Skill 输入 token 略高，主要来自 skill 说明与 schema 读取开销，但换来了更高成功率与更低收敛时间。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── pipeline/
│   ├── services/
│   ├── broken_outputs/
│   ├── vendor/
│   └── skills/
├── tests/
├── solution/
└── README.md
```
