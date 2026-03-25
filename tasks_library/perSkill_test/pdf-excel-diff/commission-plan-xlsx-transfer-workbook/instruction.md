你在帮助销售运营团队整理月度提成结算文件。

输入文件：
- `/root/sales_detail_2026Q1.xlsx`：销售明细，使用工作表 `Closed Deals`
- `/root/team_quota_plan_2026.xlsx`：销售配额与提成率，使用工作表 `Rep Targets`

请创建 `/root/commission_payouts.xlsx`。输出工作簿必须且只能包含以下 3 个工作表，顺序也必须一致：

1. `Quota Plan`
2. `Commission Detail`
3. `Team Overview`

具体要求：

`Quota Plan`
- 从 `Rep Targets` 复制以下列，保持列名完全一致：
  - `rep_id`
  - `rep_name`
  - `team`
  - `monthly_quota`
  - `standard_rate`
  - `stretch_rate`

`Commission Detail`
- 每条销售明细保留一行，并按 `sale_id` 升序排列。
- 列必须按以下顺序输出：
  - `sale_id`
  - `sale_month`
  - `rep_id`
  - `rep_name`
  - `team`
  - `client`
  - `net_revenue`
  - `monthly_quota`
  - `monthly_revenue`
  - `attainment`
  - `applied_rate`
  - `commission`
- `rep_name`、`team`、`monthly_quota` 必须通过引用 `Quota Plan` 的公式填充。
- `monthly_revenue` 必须用公式计算“同一个 `rep_id` 在同一个 `sale_month` 的总 `net_revenue`”。
- `attainment` 必须用公式计算 `monthly_revenue / monthly_quota`。
- 当 `attainment >= 110%` 时，`applied_rate` 使用 `stretch_rate`；否则使用 `standard_rate`。这一列必须是公式。
- `commission` 必须用公式计算 `net_revenue * applied_rate`，并保留两位小数。

`Team Overview`
- 按 `team` 升序输出，每个团队一行。
- 列必须按以下顺序输出：
  - `team`
  - `quota_total`
  - `total_revenue`
  - `total_commission`
  - `attainment`
- `quota_total` 必须通过引用 `Quota Plan` 的公式汇总。
- `total_revenue` 和 `total_commission` 必须通过引用 `Commission Detail` 的公式汇总。
- `attainment` 必须用公式计算 `total_revenue / quota_total`。

通用要求：
- `Commission Detail` 中的 `rep_name`、`team`、`monthly_quota`、`monthly_revenue`、`attainment`、`applied_rate`、`commission` 必须都是公式单元格，不能把最终结果直接写死。
- `Team Overview` 中除 `team` 外的列都必须是公式单元格。
- 公式重算后不能出现 `#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?`、`#N/A` 等错误。
- 除非为了可读性添加少量格式，否则不要改动列名、工作表名称或输出路径。
