# Incident: SLA Audit Failed on Cross-Region Shipments

日期：2026-03-20

复盘摘要：

- 一部分订单与履约事件来自不同时区的系统。
- 数据表结构正常、任务也能跑完，但 publish audit 在 SLA 复核阶段失败。
- 事故说明：只要时间基准没有统一，按时发货判断和日终日期都可能被翻转。

处理要求：

- 先统一时间基准，再比较发货时效。
- `snapshot_date` 与 SLA 口径需要共享同一套时间归一化规则。
