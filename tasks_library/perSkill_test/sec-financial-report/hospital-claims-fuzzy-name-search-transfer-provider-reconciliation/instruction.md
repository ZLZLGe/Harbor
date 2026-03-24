你在一家健康险公司的支付完整性团队做网络内理赔核对。输入文件已经放在：

- `/root/provider_master.csv`
- `/root/drug_catalog.csv`
- `/root/medical_claims.csv`

这些文件里的医院名和药品名都存在缩写、错拼或别名，不能直接依赖精确字符串匹配。

请完成下面的任务，并把最终结果写入 `/root/claims_reconciliation.json`：

1. 目标网络定位
   使用不规范医院名 `st mary med ctr westlk`，在 `provider_master.csv` 中定位标准医疗机构。
   以该机构所属的 `network_id` / `network_name` 作为目标医院网络。

2. 重点高费用药品定位
   使用下面 3 个不规范药品搜索词，在 `drug_catalog.csv` 中分别定位标准药品记录：
   - `keytrudaa`
   - `nivolimab`
   - `herzumaa`

3. 理赔标准化与汇总
   对 `medical_claims.csv` 中每条理赔记录：
   - 将 `provider_name_raw` 对齐到标准 `provider_id`
   - 将 `drug_name_raw` 对齐到标准 `drug_code`

   然后只保留同时满足下面两个条件的理赔：
   - 标准化后的 `provider_id` 属于第 1 步确定的目标网络
   - 标准化后的 `drug_code` 属于第 2 步定位出的 3 个重点高费用药品

4. 计算网络指标
   对上一步筛出的理赔，计算：
   - `high_cost_claim_count`：理赔条数
   - `denied_high_cost_claim_count`：`status = DENIED` 的条数
   - `denial_rate`：`denied_high_cost_claim_count / high_cost_claim_count`，保留 6 位小数
   - `high_cost_paid_amount`：`paid_amount` 总和

5. 输出异常理赔清单
   在筛出的理赔里，满足任一条件即视为异常：
   - `status = DENIED` 且 `allowed_amount >= 50000`
   - `status = PAID` 且 `paid_amount > units * reference_unit_paid_amount * 1.25`

   对每条异常理赔，输出：
   - `claim_id`
   - `provider_id`
   - `provider_name`
   - `drug_code`
   - `canonical_name`
   - `status`
   - `allowed_amount`
   - `paid_amount`
   - `reference_paid_amount`
   - `anomaly_reason`

输出 JSON 必须严格符合下面的 schema：

```json
{
  "anchor_provider_search_term": "st mary med ctr westlk",
  "resolved_anchor_provider": {
    "provider_id": "string",
    "provider_name": "string",
    "network_id": "string",
    "network_name": "string"
  },
  "resolved_high_cost_drugs": [
    {
      "search_term": "string",
      "drug_code": "string",
      "canonical_name": "string",
      "brand_name": "string"
    }
  ],
  "network_metrics": {
    "network_id": "string",
    "network_name": "string",
    "high_cost_claim_count": 0,
    "denied_high_cost_claim_count": 0,
    "denial_rate": 0.0,
    "high_cost_paid_amount": 0.0
  },
  "anomalous_claims": [
    {
      "claim_id": "string",
      "provider_id": "string",
      "provider_name": "string",
      "drug_code": "string",
      "canonical_name": "string",
      "status": "string",
      "allowed_amount": 0.0,
      "paid_amount": 0.0,
      "reference_paid_amount": 0.0,
      "anomaly_reason": "string"
    }
  ]
}
```

额外要求：

- `resolved_high_cost_drugs` 必须按搜索词给定顺序输出。
- `anomalous_claims` 必须按 `claim_id` 升序输出。
- 所有金额字段都输出数字，不要输出字符串。
