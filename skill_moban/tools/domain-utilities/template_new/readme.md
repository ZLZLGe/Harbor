# Domain Acquisition Opportunity Research

本模板面向 `domain-utilities` 类任务，重点对齐 SkillsMP 中高相关的 `domain-name-brainstormer`、`domain-research`、`domain-authority-auditor` 和 `typosquatting / dnstwist` 一类能力，但任务形态不是开放式 brainstorming，也不是修某个应用，而是一份真实风格的域名收购研究交付。Solver 需要围绕冻结的市场简报、候选域名池、authority 指标、法律风险标记、可比交易和本地 lookup 链路，生成一份可复核、可解释、可排名的机会报告。

## 📌 任务元数据

- 任务 ID：`domain-utilities__domain-acquisition-opportunity-research`
- 类别：`domain-utilities`
- 难度：`hard`
- 绑定 Skill：`domain-acquisition-research`
- 环境形态：单容器；容器内同时提供冻结数据、本地 lookup 服务和正式输出目录
- 交付物：`/app/output/opportunity_report.json`

这个模板对应的是更接近 CorpDev / brand operations / launch operations 的 workflow：

- 先从候选池、市场简报和本地 lookup 服务恢复真实决策上下文；
- 再按公开 scoring policy 计算 market fit、authority、commercial intent 和 legal risk；
- 最后把结论收口成结构化 shortlist，而不是写一篇难以验证的开放式报告。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 2026-04-22，`domain-template-oracle-20260422e` / `task_with_skills_e2b__mj82Kgp`
- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`8/8` 通过
- 对应最终版任务 checksum：`87b7a179a1ce3b97ffe54451da08f65d3c1d9e1840a2af29ce0c9253f45d8755`

Verifier 策略：

- 主测：检查 `opportunity_report.json` 是否存在、可解析、字段完整且排序规则正确。
- 主测：从冻结的 `candidate_domains.csv`、`authority_metrics.csv`、`sales_comps.csv`、`trademark_flags.csv`、`archive_summaries/` 和本地 snapshot 服务动态重算各域名得分，验证 `status`、`price_ceiling_usd`、`total_score`、`buy_now_ranked` 和 `top_pick`。
- 主测：检查 `reason_codes` 和 `evidence` 是否真正对应到策略、archive、authority、legal 和本地 snapshot 来源，而不是模板化 narrative。
- 防作弊：保护原始数据、本地 lookup 服务和 shipped skill 文件；拦截删除候选项、伪造 evidence、忽略法律/价格约束、以及硬编码最终 top3 的 shortcut。

数据质量：

- 数据是冻结的域名研究快照，覆盖 market brief、候选域名特征、authority 信号、交易可比、法律风险和 archive 主题匹配。
- 其中 RDAP / listing / DNS 风格 snapshot 不以可见原始 JSON 直接暴露，而是通过单容器内的 localhost lookup 服务提供。
- 数据结构具有真实业务复杂度：评分公式跨多源输入，且最终结论不能只靠单一分数字段直接排序。
- verifier 关注行为结果，不绑定某一套脚本写法。

数据来源：

- `archive_summaries/`：冻结的 Wayback-style 历史主题摘要，用来模拟 archive 语义回查。
- `sales_comps.csv`：冻结的可比成交样本，按 NameBio-style comp family 组织。
- `authority_metrics.csv`：冻结的 referring domains / trust / continuity 指标，模拟 SEO authority 审计输入。
- localhost snapshot API：冻结的 RDAP / registrar inventory / DNS 风格快照，经容器内 `127.0.0.1:8331` 服务提供。
- 评测不依赖外部网站实时请求；真实性来自数据形态、证据链和本地 lookup 工作流，确定性来自全量冻结快照。

多模态：

- 不适用（纯文本 / 结构化数据 / 本地 API 任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是直接给出最终排名，而是把最容易出错的诊断路径标准化：

- 先读取 localhost manifest，确认哪些 lookup 端点和证据字段属于正式链路；
- 再对候选池、authority、legal 和 archive 结果做统一重算，尽早暴露公式理解偏差；
- 然后把 per-domain evidence 收口成固定来源，减少“分算对了但证据写散了”的错误；
- 最后再整理结构化输出，避免只写 top3 却漏掉全量候选覆盖。

with_skill vs without_skill 对照实验：

- 结论：强相关。这个任务里，Skill 的核心价值是把 localhost manifest 探测、snapshot 拉取、策略重算和 evidence 打包标准化；`without_skill` 不是不会算分，而是更容易在最后一步把证据锚点写散，稳定卡在 `test_e_reason_codes_and_evidence_are_grounded`。
- 基于 2026-04-22 最近 `3` 次最终版有效对照实验（已排除平台启动失败 trial，如 `BuildException: build was cancelled`）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | With Skill 已稳定通过；Without Skill 仍全部失败 |
| 总耗时 | `361.4s` | `280.2s` | With Skill 更快，平均总耗时降低约 `22.5%` |
| Agent 执行耗时 | `276.1s` | `199.2s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `27.9%` |
| Input Tokens | `515,255` | `321,843` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.60x` |

- 最终版有效样本：
- `with_skill`：`domain-template-with-skills-20260422l`、`domain-template-with-skills-20260422n`、`domain-template-with-skills-20260422o`
- `without_skill`：`domain-template-without-skills-20260422e`、`domain-template-without-skills-20260422f`、`domain-template-without-skills-20260422g`
- checksum 对齐：
- 三次 `with_skill` 结果共享最终版 checksum `87b7a179a1ce3b97ffe54451da08f65d3c1d9e1840a2af29ce0c9253f45d8755`
- 三次 `without_skill` 结果共享 checksum `9389f0254db02a1ff9509ea8100330378775cd79451fa160b2cc2c4ce15abb35`
- 两组运行时的唯一区别来自 `environment/skills/` 复制内容；题面、测试、数据、依赖与环境链路保持一致。
- 失败模式：
- `without_skill` 三次都稳定失败在 `test_e_reason_codes_and_evidence_are_grounded`
- 典型症状是 `calltitanhq.com` 的 evidence 锚点来源名或字段规范不一致，说明难点集中在“把多源证据收敛成 verifier 认可的行为结果”，而不是简单硬编码 top pick。

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
