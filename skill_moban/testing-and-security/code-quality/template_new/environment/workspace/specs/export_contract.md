# Merchant Settlement Export Contract

这条导出链路面向 merchant settlement reconciliation。正式 gate 只接受两类报表：

1. `daily`
   - 以 `report_date + merchant_id + currency` 为唯一键
   - 需要输出 `processor_batch_id`
   - 需要同时体现 `gross_amount`、`fee_amount`、`adjustment_amount` 和 `net_settlement_amount`
   - `net_settlement_amount = gross_amount - fee_amount + adjustment_amount`

2. `monthly`
   - 以 `report_month + merchant_id + currency` 为唯一键
   - 需要保留 `refund_count` 与 `chargeback_count`
   - 需要保留 `first_batch_id` / `last_batch_id`
   - 需要和 daily 行为一致，不能在月汇总时重新定义净额口径

约束：

- `refund`、`chargeback`、`manual_adjustment`、`reserve_release` 都属于 adjustment 侧，不允许静默丢弃。
- `processor_batch_id` 为空时，必须退回到同记录的 fallback batch id；下游验收不会接受空 batch。
- 这条链路的目标不是“看起来有文件”，而是“结果能被 settlement gateway 接受”。
