## 📌 任务元数据

- 任务 ID：`compchem__leadlike-screening-shortlist`
- 任务名称：`Lead-Like Screening Shortlist`
- 任务类别：`computational-chemistry`
- 任务目标：在单容器 RDKit 环境中，从冻结的小分子库里真实完成结构解析、标准化、去重、性质计算、结构警报判定、与参考活性分子的相似性计算，以及稳定 shortlist 排序。
- 官方输出：`/root/workspace/solution.py`
- 绑定 Skill：`rdkit-screening-diagnostics`
- 对照口径：`with_skill` 与 `without_skill` 的唯一区别只来自 `environment/skills/` 及其 runtime 剥离逻辑；题面、数据、测试、依赖和 verifier 完全一致。

## 📊 验证与测试指标（Oracle & Verifier）

e2b Oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- Job：`compchem-template-oracle-20260421-sem4`
- Trial：`task_oracle_e2b__CopGwPe`
- 测试用例：`9/9` 通过

Verifier 策略：

- 主测：校验返回 schema 与 summary 计数、盐型/重复表示合并且保留立体化学、代表化合物描述符和 alerts、`Morgan(radius=2, nBits=2048, includeChirality=True)` 相似度、以及稳定排序行为。
- 防作弊：打乱输入顺序与文件名后结果不变、替代 fixture 仍能泛化、交换 metadata 名称不影响行为、禁止 all-keep / all-reject 这类表层规避。
- 行为约束：verifier 关注最终行为结果，不绑定唯一实现；`reasons` 做语义校验而不是字符串逐字绑定。

数据质量：

- 数据来源：任务库中的分子结构基于 PubChem Compound 公开记录整理并冻结，覆盖 ibuprofen、naproxen、ketoprofen、lidocaine、caffeine、warfarin 等常见药化分子，并补入供应商元数据、参考活性集和显式规则文件。
- 数据结构：同时提供 `.sdf`、`.smi` 和 `vendors.csv`，包含盐型重复、异构体、alert-positive 分子、边界 lead-like 分子，能真实触发标准化与诊断流程。
- 确定性：参考集、规则和排序配置均固定在 `actives.csv`、`rules.json`、`scoring.json`，保证可复现和可测。

多模态：

- 不适用（纯 Python/RDKit 后端任务，无浏览器或图像链路）。

## ⚡ Skill 相关性评估

结论：强相关。

2026-04-21 检查 SkillsMP 的 `computational-chemistry` 分类页时，和本任务最相关的高热度技能集中在 `drug-discovery.md`、`rdkit.md`、`medchem.md`、`datamol.md`、`chemistry-rdkit.md`、`cli-anything-unimol-tools.md` 这一簇。这个模板没有去做更重的 docking 或分子 ML，而是刻意对齐其中最稳定、最常见、最可验证的交集能力：真实分子文件解析、结构标准化、描述符计算、指纹相似度、药化过滤与 deterministic ranking。

本题里 Skill 的核心价值不是“直接给答案”，而是把诊断路径标准化：

- 先探测解析与标准化行为，避免把盐型/重复表示/立体异构体错误合并。
- 先探测描述符与规则投影，避免把 lead-like 失败原因做错。
- 先探测 InChI 支持，识别当前 Debian `python3-rdkit` runtime 不提供可用 InChI backend，从而选择任务可接受的确定性 fallback，而不是伪造 hash 风格 `inchikey`。

基于最近 `3` 次有效 `with_skill` trial 与最近 `3` 次有效 `without_skill` trial（均为真实 task-level 运行，存在完整 agent 轨迹，已排除启动失败类样本）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | With Skill 已稳定通过；Without Skill 未出现通过 |
| 平均总耗时 | `508.6s` | `316.8s` | With Skill 更快，平均总耗时降低约 `37.7%` |
| 平均 Agent 执行耗时 | `386.5s` | `233.7s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `39.5%` |
| 平均 Input Tokens | `615,254` | `298,480` | Without Skill 的上下文与试错开销约为 With Skill 的 `2.06x` |

失败模式归纳：

- `without_skill` 最近 3 个有效样本都稳定卡在 `3` 个 verifier：`test_end_to_end_matches_reference_behavior`、`test_shuffled_input_order_and_filenames_do_not_change_behavior`、`test_alternate_fixture_generalizes`。
- 共同根因是 agent 没有先确认 runtime 的 InChI 能力，转而生成了伪造或不被当前任务接受的 `inchikey` 表示；而 verifier 期望的是确定性化学回退行为。
- `with_skill` 的 3 个有效样本都取得了 `9/9` 通过；从 sem5 轨迹可直接看到样本会先探测 runtime 的 InChI 能力，并在 `INCHI_AVAILABLE = false` 时收敛到可接受 fallback，整体收敛方向与 skill 设计一致。

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   │   ├── library/
│   │   └── reference/
│   └── skills/
│       └── rdkit-screening-diagnostics/
│           ├── SKILL.md
│           └── scripts/
├── tests/
│   ├── conftest.py
│   ├── test_outputs.py
│   ├── test_guardrails.py
│   ├── test.sh
│   └── fixtures_alt/
└── solution/
    ├── fixed_solution.py
    └── solve.sh
```

说明：

- `environment/` 使用单容器实现，容器内同时承载真实任务数据、solver 工作区和 task-bound skill。
- `tests/` 同时包含主测试与 guardrails，验证真实行为结果而不是某一种固定实现。
- `solution/` 提供官方参考修复与一键求解脚本，oracle 在 e2b 下稳定通过。
