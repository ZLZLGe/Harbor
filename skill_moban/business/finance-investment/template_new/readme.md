# Finance Investment Template Design

## 第一部分：任务设计参考

* **Skill 价值定位**：技能收益必须体现在金融分析中最容易耗时、出错且可被标准化的部分，例如公开财报字段定位、SEC XBRL concept fallback、财年口径选择、价格/基准/利率日期对齐、DCF 假设落地、风险指标计算和跨文件一致性校验；严禁把 skill 价值建立在题面提示、隐藏答案、改 verifier、改数据、改依赖或替换真实计算链路上。
* **任务目标形态**：任务应要求 Agent 基于公开来源冻结数据完成可复核的金融分析交付物，例如财报指标表、风险评分表、估值 JSON、投资排序和研究备忘录；不应设计成单纯修 app、猜 puzzle、只填一个隐藏答案、只做格式搬运或依赖实时联网结果的任务。
* **验证设计重点**：Verifier 应从公开输入数据独立重算关键结果，关注行为结果和跨交付物一致性，而不是绑定某个唯一实现；同时应包含 guardrails，防止修改输入、伪造输出、替换 JSON 顶层结构、写占位内容或绕过真实计算。

设计要点：

* 数据应来自真实公开来源，但在环境中冻结为本地文件，保证 E2B 可重复验证。
* instruction 只能描述业务任务、输入、输出和禁止事项，不应出现 skill 名称或引导 solver 使用 skill。
* with_skill 和 without_skill 的唯一区别必须只来自 `environment/skills/` 及 Dockerfile 中对应的 skill 复制逻辑。
* without_skill 必须理论可解，但诊断/定位/收敛成本显著更高，并且正式对照中至少保留一项 verifier 失败。

## 第二部分：示例任务

该示例任务面向 SkillsMP finance-investment 热门方向：公开财报分析、公司质量评分、市场风险指标、DCF 估值和投资建议排序。任务风格对齐 finance reference：给定公开来源冻结数据，按明确金融口径计算，输出结构化答案文件，而不是修复 app 或依赖隐藏答案。

### 📌 任务元数据

- 任务 ID：`finance-investment__public-equity-quality-risk-valuation`
- 类别：`finance-investment`
- 难度：`hard`
- 主输出：`/app/output/investment_ranking.json`
- 输入来源：SEC EDGAR Company Facts、Yahoo Finance chart endpoint、FRED DGS10
- 输出文件：`financial_metrics.csv`、`quality_risk_scores.csv`、`valuation.json`、`investment_ranking.json`、`research_memo.md`

### 📊 验证与测试指标（Oracle & Verifier）

- E2B oracle 结果：✅ 通过（Reward: `1.0`）
- Oracle job：`finance-investment-oracle-final`
- Trial：`finance-investment__8UFRFcG`
- 测试用例：`11/11` 通过（`11 passed in 2.60s`）

Verifier 策略：

- 主测：从 SEC Company Facts、价格 CSV 和 FRED CSV 重算财务指标、252 日风险指标、DCF 估值、composite score、排名、建议和 memo 一致性。
- 防作弊：校验公开输入文件 hash，检查输出非占位/非 NaN/非 Inf，限制 JSON 顶层结构，确保不能替换 payload 或绕过真实计算。

数据来源：

- SEC EDGAR Company Facts API：https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC Company Facts bulk archive：https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
- FRED DGS10：https://fred.stlouisfed.org/series/DGS10
- Yahoo Finance chart endpoint：https://query1.finance.yahoo.com/v8/finance/chart/

多模态：

- 不适用（纯结构化公开金融数据与 Markdown 报告任务）。

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 SEC Company Facts 概念族、10-K/FY fact 选择、capex/share fallback、252 日风险对齐、DCF 假设、ranking tie-break 和跨文件一致性检查标准化。without_skill 理论上可以解，但在真实 trial 中更容易把 fiscal year、XBRL concept 或评分排序口径做偏。

基于最近 3 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | With Skill 三次全通过；Without Skill 三次均至少保留 verifier 失败 |
| 总耗时 | `482.1s` | `191.4s` | With Skill 平均总耗时降低约 `60%` |
| Agent 执行耗时 | `385.4s` | `88.1s` | With Skill 平均 Agent 耗时降低约 `77%` |
| Input Tokens | `680,998` | `219,277` | Without Skill 的上下文与试错开销约为 With Skill 的 `3.11x` |

常见 without_skill 失败点：

- `financial_metrics.csv` 未按 verifier 口径重建 SEC fiscal-year facts。
- `quality_risk_scores.csv` 的质量/风险分数和 composite ranking 偏离。
- `investment_ranking.json` 与结构化分数或建议规则不一致。
- `research_memo.md` 与 JSON/CSV 输出不完全一致。

### 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   └── skills/
├── tests/
│   ├── test.sh
│   ├── reference_metrics.py
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── solve.sh
    ├── solve.py
    └── reference_metrics.py
```

with_skill / without_skill 对照中，唯一差异为 `environment/skills/` 及 Dockerfile 中对应的 `COPY skills ...` 复制逻辑；题面、测试、数据、依赖和 skill 本体均不在实验中修改。
