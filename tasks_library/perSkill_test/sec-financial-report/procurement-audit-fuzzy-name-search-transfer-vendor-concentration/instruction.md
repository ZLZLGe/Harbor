你在市审计署的采购审计组，正在复核一批基础设施采购。输入文件已经放在：

- `/root/vendor_master.csv`
- `/root/contract_awards.csv`
- `/root/payment_ledger.csv`

这些文件中的供应商名称存在缩写、旧称、标点差异和轻微拼写变体，不能直接依赖精确字符串匹配。

本题的关键在于先完成本地的供应商名称模糊归一，再进行后续授标与付款汇总分析。请直接参考当前唯一 shipped skill `fuzzy-name-search`：它的示例脚本虽然面向 13F 基金/股票名称检索，但核心可迁移点就是先做名称规范化，再用模糊字符串打分来选择最接近的标准名称。这里不要查远程数据，也不要引入额外数据源，只把 `fuzzy-name-search` 里的这套本地模糊匹配思路迁移到这 3 份 CSV 的供应商归一上即可。

请完成下面的任务，并把最终结果写入 `/root/vendor_concentration_report.json`：

1. 供应商标准化
   对 `contract_awards.csv` 中的 `vendor_name_award` 和 `payment_ledger.csv` 中的 `payee_name_raw`，
   都匹配到 `vendor_master.csv` 里的标准供应商记录，得到统一的：
   - `vendor_id`
   - `vendor_name`
   - `parent_group_id`
   - `parent_group_name`

2. 目标部门
   只分析 `department_code = DPT-410`、`department_name = Department of Water Infrastructure` 的合同和付款。

3. 前五大供应商
   对目标部门内的标准化供应商，按 `vendor_id` 聚合并计算：
   - `contract_count`：该供应商在目标部门的合同数
   - `awarded_amount`：这些合同的 `award_amount` 之和
   - `paid_amount`：这些合同对应付款的 `payment_amount` 之和

   取 `paid_amount` 最高的前 5 家供应商。
   排序规则：
   - 先按 `paid_amount` 降序
   - 如有并列，再按 `vendor_id` 升序

4. 集团合并后的采购集中度
   将目标部门内的 `paid_amount` 按 `parent_group_id` 合并，计算：
   - `department_total_paid`
   - `top_group_id`
   - `top_group_name`
   - `top_group_paid`
   - `top_group_share = top_group_paid / department_total_paid`
   - `cr3`：前三大集团支付占比之和
   - `hhi`：按集团支付占比计算的 Herfindahl-Hirschman Index，使用 0 到 1 的比例口径，即 `sum(share^2)`

   所有比例字段保留 6 位小数。

5. Stormwater Retrofit 超预算付款
   只看目标部门里 `project_category = Stormwater Retrofit` 的合同。
   对每个合同，按 `payment_date`、`payment_id` 升序累计付款。
   任何一笔付款只要使该合同的 `cumulative_paid_after_payment` 严格大于 `award_amount`，就视为超预算付款，输出该笔付款。

6. 输出格式
   输出 JSON 必须严格符合下面的 schema：

```json
{
  "target_department": {
    "department_code": "DPT-410",
    "department_name": "Department of Water Infrastructure"
  },
  "focus_project_category": "Stormwater Retrofit",
  "top_vendors": [
    {
      "rank": 1,
      "vendor_id": "string",
      "vendor_name": "string",
      "parent_group_id": "string",
      "parent_group_name": "string",
      "contract_count": 0,
      "awarded_amount": 0.0,
      "paid_amount": 0.0
    }
  ],
  "group_concentration": {
    "department_total_paid": 0.0,
    "top_group_id": "string",
    "top_group_name": "string",
    "top_group_paid": 0.0,
    "top_group_share": 0.0,
    "cr3": 0.0,
    "hhi": 0.0
  },
  "over_budget_payments": [
    {
      "payment_id": "string",
      "payment_date": "YYYY-MM-DD",
      "contract_id": "string",
      "vendor_id": "string",
      "vendor_name": "string",
      "project_category": "string",
      "payment_amount": 0.0,
      "award_amount": 0.0,
      "cumulative_paid_after_payment": 0.0,
      "over_budget_amount": 0.0
    }
  ]
}
```

额外要求：

- `top_vendors` 必须正好包含 5 个对象，并写入正确的 `rank`。
- `over_budget_payments` 必须按 `payment_date`、`payment_id` 升序输出。
- 所有金额和比例字段都输出数字，不要输出字符串。
