# Incident: Missed Adjustments Were Silently Dropped

时间：2026-04-12

症状：

- 日报仍然生成成功
- finance 人工复核时发现净额偏高
- 根因排查显示某些 adjustment 没进入正式导出

已确认的事故特征：

- 不是所有脏数据都会触发显式异常
- `refund` 和 `chargeback` 一旦被过滤掉，文件依然“长得像对的”
- 如果只盯着 charge happy path，很容易漏掉这类问题

这次事故的经验要求：

- 正式质量 gate 必须包含 dirty replay
- 功能测试不能只覆盖 charge-only 样例
