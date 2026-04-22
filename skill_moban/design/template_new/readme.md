# Design 模板任务说明

## 📌 任务元数据

- 任务名：`design__launch-storyboard-html-deck-delivery`
- 类别：`design`
- 难度：`hard`
- 绑定 Skill：`launch-deck-diagnostics`
- 任务形态：浏览器原生 HTML launch deck 交付，不是 app 修 bug，也不是静态长图题

这个模板对齐 SkillsMP design 分类里高信号的 `frontend-slides`、`concept-diagrams`、`popular-web-designs` 一类技能，核心是“把一份内部评审稿收敛成正式可交付 deck”。Solver 会拿到冻结的 brief、KPI、能力矩阵、客户证据、用户旅程拓扑、品牌镜像，以及一份可见的内部评审稿 `/app/workspace/drafts/internal_review_draft.html`；最终必须交付浏览器可直接打开的 `/app/output/deck/index.html`，并通过真实 localhost `manifest -> validate` QA 链路生成正式 `deck_submission.json` 与 `deck_receipt.json`。

环境是单容器实现，保留了真实风格的交付链路：

- `workspace/`：冻结输入资料与内部评审 draft
- `render-qa-service/`：localhost 渲染与验收服务
- `skills/launch-deck-diagnostics/`：manifest 探测、draft staging、诊断、打包与提交脚本
- `tests/`：行为结果主测与防作弊 guardrails

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1`）
- 测试用例：`1/1` 通过
- 参考作业：`design-template-oracle-20260422i1`

Verifier 策略：

- 主测：检查 `/app/output/deck/index.html`、`/app/output/deck_submission.json`、`/app/output/deck_receipt.json` 是否真实存在；6 个全屏 slide 是否完整；导航、来源追溯、结构化 KPI 图表、结构化 journey 图、localhost QA receipt 是否同时成立。
- 主测：`browser_contract` 会在 `1440x900` 和 `1280x720` 两个视口下真实打开 deck，验证翻页、活跃 slide 指示、主要内容无滚动依赖、无明显越界裁切。
- 主测：`story_fidelity` 会核对 quote provenance、comparison 机器可读状态、journey 覆盖、risk/boundary 表述是否仍然忠于冻结输入。
- 防作弊：拦截手写 receipt、伪造 submission、截图拼页、长滚动伪 slide、删除 required roles、删除图表或流程图、外链依赖、硬编码固定 KPI / capability / journey 节点等规避方式。

数据质量：

- 数据是仓内冻结的真实风格 launch narrative 资料，不在线抓取，保证确定性与可测性。
- 输入同时覆盖 brief、品牌镜像、周度 KPI、能力矩阵、客户证据、journey topology 和内部评审 draft，足以支撑信息设计、图表表达、流程图表达与来源追溯。
- 内部评审稿不是答案文件；它能通过部分结构检查，但默认仍会在 story fidelity 和正式提交流程上暴露真实缺口。

数据来源：

- `/app/workspace/brief/creative_brief.md`
- `/app/workspace/mirror/site/`
- `/app/workspace/data/weekly_kpis.csv`
- `/app/workspace/data/feature_matrix.csv`
- `/app/workspace/data/customer_quotes.json`
- `/app/workspace/data/user_journey.json`
- `/app/workspace/drafts/internal_review_draft.html`

多模态：

- 不适用（这是浏览器原生 HTML 交付任务；最终验证聚焦 DOM、渲染、布局、来源追溯与 localhost QA 行为）。

## ⚡ Skill 相关性评估

结论：中等偏强相关。

这个任务里，Skill 的价值不在于替 solver 设计页面，而在于把最容易高成本试错的链路标准化：先把内部评审稿 staging 到正式输出路径，再用 manifest、结构检查、story fidelity、browser contract 和最终提交流程逐步收敛。没有 skill 时，任务依然理论可解，但 solver 需要自己摸出 draft 如何落位、哪些隐藏 fidelity 约束会卡住、怎样打包 submission，以及何时才应该触发正式 QA。

基于最近 `3` 次有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `66.7%` | `100%` | With Skill `3/3` 通过；Without Skill 仅 `2/3` 通过，仍有真实 verifier 失败样本 |
| 总耗时 | `1381.9s` | `448.8s` | With Skill 更快，平均总耗时降低约 `67.5%` |
| Agent 执行耗时 | `723.7s` | `373.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `48.4%` |
| Input Tokens | `1.82M*` | `1.52M` | 目前可见的 non-timeout Without 样本 token 开销约为 With 平均值的 `1.20x` |

补充说明：

- 使用的 with-skill 样本：`design-template-with-skills-e2b-20260422i1/i2/i3`
- 使用的 without-skill 样本：`design-template-without-skills-e2b-20260422i1/i2/i3`
- `without i1`、`without i2` 都触发了 `AgentTimeoutError`，但由于超时前正式输出与 localhost receipt 已经齐全，按任务规则仍计为通过。
- `without i3` 为真实失败样本，主因是没有产出正式 `deck_submission.json` 与 `deck_receipt.json`，导致多项主测失败。
- `*` 两个 timeout-pass 的 without 样本没有 Harbor 级 token 统计，因此 Without 的 token 行按仅有的 non-timeout 失败样本展示，并在这里显式注明。

Skill 相关性说明：

- Skill 明显降低了“先把 draft 放到正式输出路径、再跑完整诊断链”的收敛成本。
- 任务仍然没有退化成“只有 skill 才能做”的 hidden-answer puzzle；without 依然可能在高成本试错后成功。
- 这也意味着该模板更适合评估“诊断标准化与收敛稳定性”，而不是追求绝对的二元分离。

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   ├── render-qa-service/
│   └── skills/
├── tests/
└── solution/
```
