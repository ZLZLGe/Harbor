# Incident: Blank Batch IDs Rejected by Gateway

时间：2026-04-16

症状：

- 某批报表内容看上去完整
- 但 gateway 仍然拒收，原因是部分行的 batch id 为空

已确认的事故特征：

- 某些 adjustment 行没有 `processor_batch_id`
- 如果没有回退到 fallback batch id，下游会把整批视为不合规
- 这类问题不一定影响本地聚合结果，但会影响真实交付

这次事故的经验要求：

- 本地测试不能只验证金额
- integration gate 需要真正跑到 gateway
