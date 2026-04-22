# SaaS Board Growth Diagnostics Bundle

本模板面向 `data-analysis` 类 skill 任务，风格对齐 Harbor / SkillsBench 里更接近真实工作流的分析型案例，而不是代码修复型题。它综合了 SkillsMP 中高热度的 `data-analyst`、`startup-metrics-framework`、`data-storytelling`、`kpi-dashboard-design`、`visualization-expert` 这类能力诉求：solver 需要从冻结的多表经营数据出发，形成一套可复核、可审计、可提交的董事会经营分析包。

## 📌 任务元数据

- 任务 ID：`data-analysis__saas-board-growth-diagnostics-bundle`
- 类别：`data-analysis`
- 难度：`hard`
- 绑定 Skill：`saas-board-metrics-diagnostics`
- 环境形态：单容器；容器内同时提供原始数据、正式输出目录和本地 audit API
- 核心交付物：
  - `/app/output/metrics_snapshot.csv`
  - `/app/output/diagnosis_report.json`
  - `/app/output/executive_summary.md`
  - `/app/output/final_submission.json`
  - `/app/output/audit_receipt.json`

任务的真实感来自完整链路，而不是隐藏答案文件：

- 需要跨 `orders / subscriptions / marketing / product / support` 多表收口月度指标；
- 需要把增长、风险、效率、支持/产品联动诊断组织成结构化结论；
- 需要通过真实的 `manifest -> validate-metrics -> submit-report` 本地审计链路完成最终提交；
- verifier 只看行为结果，不绑定某一种 SQL / pandas / script 实现。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`8/8` 通过
- Job：`data-analysis-template-oracle-final-v1`
- Trial：`template_new__s8PxfeF`
- Task checksum：`b532a475c010c691aab89060b05c0211025611a07355f51ac53b14ad2008d3b9`
- 时间：`2026-04-22T08:41:53Z` 到 `2026-04-22T08:42:39Z`

Verifier 策略：

- 主测：检查 5 个正式交付物是否齐全、可解析、彼此一致。
- 主测：从冻结原始数据动态重算 `metrics_snapshot.csv`，验证是否满足公开 metric contract 和最终舍入规则。
- 主测：检查 `diagnosis_report.json` 与 `executive_summary.md` 是否真正反映增长、风险、效率和支持/产品问题，而不是模板叙述。
- 主测：重放 live `manifest -> validate-metrics -> submit-report` 链路，要求最终 bundle 仍能被本地审计服务接受。
- 防作弊：校验隐藏服务入口文件哈希不变、受保护输入数据未被改写、输出不是占位文本。

数据质量：

- 数据是冻结的 benchmark-style SaaS 经营快照，覆盖 ARR 变动、渠道花费、产品激活、支持负担与退款行为。
- 结构复杂度来自真实经营分析所需的多表 join 与口径收敛，而不是随机 puzzle。
- 评测时不依赖外部网站实时抓取；确定性和可测性由冻结数据与本地审计服务保证。

数据来源：

- 数据来源为任务内置的冻结 benchmark 资产：
  - `environment/data/orders/`
  - `environment/data/subscriptions/`
  - `environment/data/marketing/`
  - `environment/data/product/`
  - `environment/data/support/`
- 不是评测时临时联网抓取的网站数据；“网站/服务”部分仅体现在容器内的本地 audit API。

多模态：

- 不适用（纯数据分析 / 结构化 JSON / Markdown 摘要任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是直接给答案，而是把最容易导致失败的那几步工作标准化：

- 先探测 live manifest 和 metric contract；
- 再对 `metrics_snapshot.csv` 做 live recomputation diff；
- 然后基于正式辅助链路收敛增长/风险/效率诊断；
- 最后把落盘文件重新组装成最终 bundle 并走 live submit。

当前最终版基于最近 `3` 次有效对照实验（均为真正跑到 task-level、存在完整 trial 产物、使用独立 E2B 隔离环境）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | 最终版中，With Skill 已稳定通过；Without Skill 仍未出现完整通过 |
| 平均总耗时 | `713.9s` | `528.6s` | With Skill 更快，平均总耗时降低约 `26.0%` |
| 平均 Agent 执行耗时 | `621.8s` | `439.0s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `29.4%` |
| 平均 Input Tokens | `2.33M` | `1.41M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.66x` |
| 平均通过测试数 | `6.0/8` | `8.0/8` | Without Skill 稳定保留 verifier 失败项；With Skill 稳定全通过 |

最终版有效对照样本：

- `pair50_v9`
  - With：`data-analysis-template-with-skills-pair50_v9 / task_with_skills_e2b__wDhJheA -> reward 1.0`
  - Without：`data-analysis-template-without-skills-pair50_v9 / task_without_skills_e2b__BzeZZeG -> reward 0.0`
- `pair51_v10`
  - With：`data-analysis-template-with-skills-pair51_v10 / task_with_skills_e2b__N6n5BAR -> reward 1.0`
  - Without：`data-analysis-template-without-skills-pair51_v10 / task_without_skills_e2b__F42vgPH -> reward 0.0`
- `pair52_v11`
  - With：`data-analysis-template-with-skills-pair52_v11 / task_with_skills_e2b__HEttR5j -> reward 1.0`
  - Without：`data-analysis-template-without-skills-pair52_v11 / task_without_skills_e2b__7DJKytA -> reward 0.0`

Without Skill 在这 3 次最终版实验里都停在相同的失败模式：

- `test_outputs.py::test_a_required_outputs_exist_and_parse`
- `test_outputs.py::test_d_final_submission_matches_saved_outputs_and_live_chain`

这说明当前模板的 skill 价值主要体现在两点：

- 把 live diagnosis/audit 工作流压缩成更低成本的标准路径；
- 显著降低因为链路诊断、文件一致性和最终 submit 收口不稳定带来的额外试错。

同时它仍然满足“without_skill 理论上可解”的要求：solver 仍能从原始数据、公开合同和 live API 出发自行构造答案，只是诊断/定位/收敛成本明显更高，且在当前时间预算内无法稳定完成闭环。

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
