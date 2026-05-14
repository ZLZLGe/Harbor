# Bioinformatics Template

这是面向 `bioinformatics` 类 skill 的模板。它综合参考 SkillsMP bioinformatics 方向热门 skill 的共性能力：对结构化实验输入做样本对齐、建模、结果导出、阈值判断和审阅收口，并把分析过程压缩成可复核的交付包。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的核心价值，是把专业分析流程收束成一条稳定链路，包括计数矩阵方向处理、样本与元数据对齐、多因素设计、统计结果提取，以及把结论整理成可交付的表格和摘要。模板任务应把难点放在分析路径和判断质量，而不是只放在文件格式。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否沿着完整分析链路完成工作，包括输入对齐、主模型与敏感性重跑是否一致使用同一批样本和基因、panel 审阅状态是否来自两套分析结果、以及 summary 能否和结果表互相印证。防作弊测试需要拦下只做 panel 子集、跳过敏感性重跑或用原始效应值替代审阅排序依据的做法。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`pasilla-release-package`
- 类别：`bioinformatics`
- 绑定 Skill：`pydeseq2`
- 输入数据参考来源：
  - `environment/data/counts/raw_counts.tsv`：任务内基因层面原始计数表；设计形态参考 Bioconductor `pasilla` 实验包中的 `pasilla_gene_counts.tsv`  
    【https://bioconductor.org/packages/3.22/data/experiment/src/contrib/pasilla_1.38.0.tar.gz】
  - `environment/data/metadata/sample_metadata.tsv`：任务内样本信息表；设计形态参考同一数据包中的 `pasilla_sample_annotation.csv`  
    【https://bioconductor.org/packages/3.22/data/experiment/src/contrib/pasilla_1.38.0.tar.gz】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出完整性 | 四个交付文件都生成且能正确读取 | 交付收束 |
| 发布结果表 | 发布模型结果来自本地 raw counts 与样本信息，并覆盖全部保留基因 | 计数矩阵方向、过滤、差异分析 |
| 归一化计数 | 归一化表与保留样本顺序、保留基因集合一致 | 样本对齐、模型输出提取 |
| panel 审阅表 | panel 基因的 release/reference 状态分类、后续动作和排序正确 | 多因素设计、敏感性重跑、审阅判断 |
| 汇总 JSON | 汇总字段能和发布结果及 panel 审阅表互相印证 | 结果汇总与审阅输出 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 模型一致性 | panel 状态必须同时反映 release 和 sensitivity rerun 两套分析 |
| 排序依赖性 | manual review 排序必须跟随主模型稳定化效应值，而不是原始效应值大小 |
| 输入依赖性 | 发布结果必须覆盖全部保留基因，不能只做 panel 子集 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务的关键难点不在于导出几张表，而在于先把 counts 与 metadata 对齐，再完成主模型、敏感性重跑、panel 审阅分类和基于稳定化效应值的人工复核排序。without_skill 更容易停在设计公式选择、系数解释和 follow-up 排序依据这类行动/分析级失败上。

基于最近 **3 组** 有效对照实验（均跑到 task-level，存在完整 agent 轨迹；已排除刚才因 provider 断流未产出结果的重跑）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 最近 3 组有效对照里，without_skill 都至少保留 1 项 verifier 失败，主要集中在主模型效应值错误、panel follow-up 状态漂移，以及 manual review 排序依据用错。with_skill 至少拿到 1 次完整通过。 |
| Agent 执行耗时 | `543.6s` | `561.7s` | without_skill 往往更早停在分析错误上，因此平均耗时略短；with_skill 会继续完成完整分析和交付。 |
| Tokens | `1.00M` | `1.07M` | 这里按输入、缓存和输出合计 tokens 统计；with_skill 成本略高，但换来了更高的任务完成度。 |

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
│   └── skills/
├── tests/
└── solution/
```
