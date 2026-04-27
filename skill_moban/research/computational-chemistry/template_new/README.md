# Computational-Chemistry Template

这是面向 `computational-chemistry` 类 skill 的模板。它综合参考 SkillsMP computational-chemistry 类热门 skill 的共性能力：SMILES/RDKit 解析、分子描述符、药物相似性、medchem 过滤、ChEMBL 风格活性归一化、ADMET/安全信号、结构告警和 lead triage 报告生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：computational-chemistry 类 skill 的核心价值，是把分子结构、活性数据和安全证据放进可复现的科学计算链路。模板任务应让 skill 在结构标准化、RDKit 描述符、单位转换、censored evidence、drug-likeness、结构告警和候选排序上降低漏项率，而不是泄露固定排名或绕过计算。
* **Task目标形态**：任务应要求 Agent 基于候选结构、活性记录、项目约束和安全摘要，产出可审计的研究报告或分析程序。目标形态适合设计成 lead triage、虚拟筛选、结构过滤、活性归一化、ADMET 预筛、series diversity 排序和方法说明，不适合做静态答案填空、网页修复或只按单一指标排序的 toy 任务。
* **Verifier设计重点**：Verifier 应重算关键化学与药物发现结果，验证输出是否来自真实结构和数据处理链路。重点应覆盖 RDKit canonical parent、MolWt/LogP/HBD/HBA/TPSA/QED、mixed-unit 活性到 nM/pActivity、censored value 处理、安全 hard exclusion、结构告警、排名连续性、动态新增候选泛化和反硬编码输出。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`computational-chemistry__offline-lead-triage`
- 类别：`computational-chemistry`
- 难度：`hard`
- 绑定 Skill：`drug-discovery`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批 candidate SMILES、ChEMBL 风格 activity records、target profile、assay notes 和 OpenFDA 风格 safety reports，独立生成 lead triage 结果。它关注候选优先级是否由真实 RDKit 结构计算、活性归一化、安全规则和多样性策略推导，而不是实现方式是否唯一。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| `lead_triage.csv/json`、`excluded_candidates.csv`、`method_notes.md` schema、rank 和 score 范围 | 可复现研究交付物与审计结构 |
| canonical parent、重复盐型合并、无效 SMILES 排除 | SMILES 解析、母体结构标准化和可追溯映射 |
| RDKit MolWt、LogP、HBD/HBA、TPSA、rotatable bonds、QED | 分子描述符与 drug-likeness 计算 |
| nM/uM/mM 转换、pActivity、confidence-weighted geometric mean、censored values | ChEMBL 风格活性归一化和带方向证据处理 |
| PAINS-like catechol、Michael acceptor、CYP interaction、hard safety exclusions | medchem 结构告警、ADMET 和安全风险整合 |
| potency/property/QED/safety/series diversity 综合排序 | lead triage、候选优先级和骨架多样性 |
| verifier 动态新增强活性候选并要求进入前列 | 数据驱动泛化、防固定名单和反硬编码排名 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把药物发现 lead triage 的关键科学口径标准化：先做 RDKit parent structure 与描述符，再处理 mixed-unit / censored activity，最后合并结构告警、安全信号和 series diversity。without Skill 理论上仍可解，但更容易在 exact mass、活性聚合、弱活性审计、duplicate parent 或动态候选泛化上失败。

基于最近 **3** 次有效对比实验（均为真实 E2B task-level Codex + GPT-5.4 轨迹；未把启动失败当作失败样本）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without Skill 三次均未完全通过；with Skill 三次均 reward `1.0`。 |
| Agent 执行耗时 | `339.4s` | `169.0s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `50.2%`。 |
| Tokens | `618.1k` | `237.9k` | Without Skill 的可统计输入 token 约为 With Skill 的 `2.60x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── services/
│   └── skills/
├── tests/
├── solution/
└── README.md
```
