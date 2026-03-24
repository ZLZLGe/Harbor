## 任务说明

`/app/workspace/monthly_statements/` 下提供了 4 份数字化月度对账单文档。每份文档都包含：

- 一组基础字段：对账单编号、账户编号、账期起始日、账期结束日、应付总额。
- 一张费用明细表：每行至少包含记账日期、费用代码、说明、金额。

请读取该目录中的所有对账单文档，按文件名升序汇总这些文档，并将结果写入 `/app/workspace/statement_metrics.json`。

输出必须是 UTF-8 编码的单个 JSON 文件，且顶层结构必须严格为：

```json
{
  "source_dir": "/app/workspace/monthly_statements",
  "statement_count": 4,
  "account_id": "同一账户编号字符串",
  "statements": [
    {
      "filename": "按文件名升序的源文档文件名",
      "statement_id": "对账单编号",
      "period_start": "YYYY-MM-DD",
      "period_end": "YYYY-MM-DD",
      "total_due": "保留两位小数的字符串",
      "fee_count": 0,
      "largest_fee": {
        "fee_code": "费用代码",
        "amount": "保留两位小数的字符串"
      }
    }
  ],
  "rollups": {
    "grand_total_due": "保留两位小数的字符串",
    "average_statement_total_due": "保留两位小数的字符串",
    "fee_counts_by_code": {
      "费用代码": 0
    },
    "fee_totals_by_code": {
      "费用代码": "保留两位小数的字符串"
    },
    "monthly_totals": [
      {
        "month": "YYYY-MM",
        "total_due": "保留两位小数的字符串",
        "fee_count": 0
      }
    ],
    "highest_total_due_statement": {
      "filename": "源文档文件名",
      "statement_id": "对账单编号",
      "total_due": "保留两位小数的字符串"
    },
    "statements_with_late_fee": [
      "包含 LATE_FEE 的源文档文件名，按文件名升序"
    ]
  }
}
```

额外要求：

- `statements` 必须按文件名升序排列。
- `monthly_totals` 必须按月份升序排列。
- `account_id` 必须来自源文档中的账户字段；4 份文档属于同一账户。
- `fee_counts_by_code` 与 `fee_totals_by_code` 只统计费用明细表中实际出现过的代码，不要补零生成额外键。
- 所有金额字段都必须写成字符串，并保留恰好两位小数。
- 不要输出额外的顶层字段，也不要把最终答案拆成多个文件。
