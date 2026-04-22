# Pasilla Batch-Aware DE Repair

## 📌 任务元数据

- 任务 ID：`bioinformatics__pasilla-batch-aware-de-repair`
- 任务类型：bulk RNA-seq differential expression repair
- 数据来源：Bioconductor `pasilla` 实验数据包
- 目标 skill：`pydeseq2_bulk_rnaseq`
- 运行环境：单容器，容器内同时提供分析链路与本地 `panel-annotation` 下游服务
- 核心目标：修复 bulk RNA-seq 差异表达发布包，使正式结果基于 `~type + condition`，并保留基线模型 `~condition` 的 panel 审计证据

## 📊 验证与测试指标（Oracle & Verifier）

- e2b oracle 结果：
  - 整体结论：✅ 通过（Reward: `1.0`）
  - 任务级结果：`1/1` 通过
  - Job：`pasilla-oracle-20260421m`

Verifier 策略：

- 主测：验证 `differential_expression.csv`、`significant_genes.tsv`、`normalized_counts.tsv`、`panel_diagnostics.tsv`、`report.json` 五类正式交付物全部存在且可解析。
- 主测：验证正式 DE 结果覆盖 `9921` 个过滤后基因，列结构、样本对齐和显著基因集合都符合合同。
- 主测：从原始 count 与 metadata 动态重跑 reference corrected/baseline 分析，检查 panel 中 `stable_treatment_signal`、`rescued_after_adjustment`、`nuisance_sensitive_drop` 三类行为是否与输出一致。
- 主测：验证 `report.json` 与表格之间的计数、上下调集合、设计公式、panel summary 和 diagnostic summary 可相互重建。
- 防作弊：对比 `environment/broken_outputs/`，确保最终 panel 可报告基因集合、panel summary 与错误交付物显著不同，且正式设计公式明确同时包含 `type` 与 `condition`。
- 防作弊：只关注行为结果，不绑定唯一实现；只要 solver 通过真实链路生成满足合同的结果即可。

数据质量：

- 原始数据来自 `pasilla` read count 矩阵与样本元数据，保留真实样本结构与技术因素 `type`。
- panel 由 `18` 个重点基因组成，稳定分成三类：`6` 个稳定信号、`6` 个校正后恢复信号、`6` 个基线误报信号。
- 注释通过容器内 HTTP 服务实时返回，不依赖静态隐藏答案文件。

数据来源：

- Bioconductor `pasilla`
- 容器内本地服务：`panel-annotation`

多模态：

- 不适用（纯数据分析 / 命令行任务）。

## ⚡ Skill 相关性评估

结论：强相关，但存在可解释的小幅波动。这个任务里，skill 的核心价值不是替 solver 直接“给答案”，而是把 `PyDESeq2` 的 corrected/baseline 双模型诊断流程、panel 审计框架，以及最终 `report.json` / `significant_genes.tsv` 的精确 schema 明确化，从而显著降低诊断和收敛成本。

最近 **3 次有效对照实验** 均基于同一任务版本与同类 E2B 运行口径；with/without 的唯一区别只来自 `environment/skills/`：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` (`0%`) | `2/3` (`66.7%`) | With Skill 已出现稳定通过案例；Without Skill 仍未通过 |
| 总耗时 | `511.0s` | `440.2s` | With Skill 更快，平均总耗时降低约 `13.8%` |
| Agent 执行耗时 | `408.2s` | `326.3s` | With Skill 的定位与收敛更快，平均 Agent 耗时降低约 `20.1%` |
| Input Tokens | `0.90M` | `0.98M` | With Skill 输入 token 略高，主要来自 skill 说明与 schema 读取开销，但换来了明显更高的成功率与更低的收敛时间 |

对应实验：

- With Skill：
  - `pasilla-with-skill-valid7-20260421` → `reward=1.0`
  - `pasilla-with-skill-valid8-20260421` → `reward=0.0`
  - `pasilla-with-skill-valid9-20260421` → `reward=1.0`
- Without Skill：
  - `pasilla-without-skill-valid6-20260421` → `reward=0.0`
  - `pasilla-without-skill-valid7-20260421` → `reward=0.0`
  - `pasilla-without-skill-valid8-20260421` → `reward=0.0`

轨迹解释：

- `with_skill-valid7` 和 `with_skill-valid9` 都成功利用了 skill 提供的 corrected/baseline 审计思路，最终产出完整 bundle 并通过 `5/5` verifier。
- `with_skill-valid8` 的唯一失败点是 `report.json.panel_summary` 中把必需键写成了 `reportable_panel_genes`，漏掉了 verifier 期望的精确键 `reportable_genes`；这不是分析思路错误，而是输出合同细节偏差。后续已在 skill 中强化这一 schema 提示。
- 三次 `without_skill` 都重新走了一遍高成本摸索路径，反复读取原始 pipeline、手工重建结果结构或半修复正式链路，但最终都至少保留了一项 verifier 失败。

## 📁 标准目录结构说明

- `instruction.md`：任务说明
- `task.toml`：任务元数据
- `PLAN.json`：任务构建过程元信息
- `environment/`：单容器环境、数据、pipeline 与绑定 skill
- `tests/`：主测试与防作弊测试
- `solution/`：官方参考修复代码与 `solve.sh`
