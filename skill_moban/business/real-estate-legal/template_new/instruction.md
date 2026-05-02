你需要为一家不良资产投资团队整理一份单标的竞拍前审查包，交付给本周投委会。容器内已经放入公开材料抓取结果，以及较早导出的内部摘要和成本表；较早导出的材料可能缺项或口径滞后。本次交付应以 `job_manifest.json` 中给出的当前容器内本地服务口径为准。

输入数据在 `/root/data/`：

- `job_manifest.json`：目标标的 ID、交付要求、输出文件和本地服务 URL。
- `source_notice_batch.pdf`：本批次官方公告 PDF。
- `source_notice_excerpt.pdf`：便于快速核查的公告摘录页。
- `source_itbi_sp.html`：圣保罗市 ITBI 页面快照。
- `source_fiduciary_law.html`：与法拍流程相关的法条页面快照。
- `source_cpc.html`：与拍卖程序相关的法条页面快照。
- `source_listing_snapshot.html`：较早保存的外部挂牌页快照，仅供背景参考。
- `stale_notice_summary.json`：较早导出的内部摘要，可能缺项或口径滞后。
- `stale_cost_sheet.csv`：较早导出的成本假设表，可能与当前口径不一致。

你的任务

1. 为目标标的整理一份结构化公告要点提取结果，覆盖投委会审查所需的关键信息。
2. 为目标标的形成一份风险登记表，明确主要风险点、风险级别、证据出处和简短说明。
3. 以当前出价口径为基础，核算买方完成交易所需的主要现金支出。
4. 为投委会写一份简短结论，说明该标的是否建议进入出价，并给出核心依据。

输出

如 `/root/output/` 不存在，请先创建该目录。

1. 写入 `/root/output/notice_extract.json`

顶层字段必须严格如下：

```json
{
  "asset_id": "",
  "edital_id": "",
  "item_number": 0,
  "auction_type": "",
  "auctioneer_name": "",
  "auctioneer_registry": "",
  "first_auction_at": "",
  "second_auction_at": "",
  "appraisal_value_brl": 0.0,
  "first_min_bid_brl": 0.0,
  "second_min_bid_brl": 0.0,
  "payment_mode": [],
  "fgts_allowed": false,
  "financing_allowed": false,
  "address": "",
  "city": "",
  "state": "",
  "registry_office": "",
  "property_registry_number": "",
  "private_area_m2": 0.0,
  "total_area_m2": 0.0,
  "taxes_responsibility": "",
  "condo_responsibility": "",
  "encumbrance_notes": "",
  "regularization_notes": "",
  "publication_at": ""
}
```

要求：

- 所有字段都必须填写，不得写 `null`、占位文本或空数组。
- 所有金额和面积字段必须为数值类型，并保留 2 位小数。
- `item_number` 必须为数值类型。
- `payment_mode` 必须是字符串数组。
- 布尔字段必须为布尔类型。
- 结果必须与当前口径一致。

2. 写入 `/root/output/risk_register.csv`

列名必须严格如下：

```csv
risk_code,risk_title,risk_level,evidence_source,summary
```

要求：

- 必须覆盖全部关键风险项。
- `risk_level` 只能是 `low`、`medium`、`high`。
- `evidence_source` 必须写明依据来自哪份输入材料或当前口径。
- `summary` 必须是简短说明，不能只写关键词。
- 风险内容应覆盖会影响出价决策、成交成本、后续持有或处置安排的关键事项。

3. 写入 `/root/output/cash_requirements.json`

顶层字段必须严格如下：

```json
{
  "asset_id": "",
  "pricing_basis": "",
  "min_bid_brl": 0.0,
  "auctioneer_fee_brl": 0.0,
  "itbi_rate_pct": 0.0,
  "itbi_brl": 0.0,
  "registry_cost_brl": 0.0,
  "modeled_tax_debts_brl": 0.0,
  "modeled_condo_debts_brl": 0.0,
  "modeled_regularization_brl": 0.0,
  "total_cash_out_brl": 0.0,
  "cash_only_flag": false,
  "financing_flag": false,
  "fgts_flag": false
}
```

要求：

- 所有金额和比例字段必须为数值类型，并保留 2 位小数。
- `pricing_basis` 必须清楚说明本次核算采用的是哪个起算口径。
- `total_cash_out_brl` 必须等于各组成项按当前口径汇总后的结果。
- 布尔字段必须与当前公告条件和成本口径一致。
- 不得跳过税费、佣金、登记或规则里要求由买方承担的项目。

4. 写入 `/root/output/investment_committee_memo.md`

内容必须包含以下一级标题，顺序不可变：

- `# Executive Summary`
- `# Auction Facts`
- `# Risks`
- `# Cash Requirement`
- `# Recommendation`

要求：

- 必须引用与前述 JSON/CSV 一致的关键事实、风险和金额。
- `# Recommendation` 中必须明确写出以下三种结论之一：
  - `BID`
  - `WATCH_ONLY`
  - `NO_BID`
- 必须说明结论的主要依据，且至少提到一项风险与一项资金约束。
- 内容应面向投委会阅读，保持简洁、可执行。

说明：

- 当前容器内本地服务的口径优先于较早导出的摘要和成本表。
- `stale_notice_summary.json` 和 `stale_cost_sheet.csv` 仅供参考。
- 不要修改 `/root/data/` 下的任何输入文件。
- 不要停掉、替换或绕过当前容器内的服务。
- 不要用缓存答案、硬编码结果或手工拼接占位内容代替核对过程。
- 不要删减风险项、删减费用项、删减交付文件，或通过改动环境来规避审查。
- 不要修改 tests、verifier、skill 文件或 environment 文件。
- 你可以在工作目录中编写辅助脚本，但最终只需要提交 `/root/output/` 下要求的 4 个文件。
