# Transfer: Alert Routing Policy Translation

`/root/AlertRouting.py` 是一个 Python 事故告警路由模块。请将它改写为 **Scala 2.13**，并把最终代码保存到 `/root/AlertRouting.scala`。

重点不是逐行照搬，而是在保持行为一致的前提下，用更符合 Scala 习惯的方式重建告警领域模型、排班窗口和升级决策流程。你的 Scala 代码至少需要提供这些组件：

- `Severity`
- `DeliveryChannel`
- `ScheduleWindow`
- `EscalationPolicy`
- `Alert`
- `EscalationStep`
- `RoutingDecision`
- `ServicePolicy`
- `AlertRouter`
- `AlertRouting` 对象，并在其中暴露 `defaultPolicies`、`routeAlert`、`routeBatch`、`summarizeByChannel`、`escalationTargets`

请满足这些要求：

- 使用 case class、sealed hierarchy、`Option`、不可变集合和表达式风格。
- 不要把 Python 里的可变列表、字典查找兜底、`None` 分支和命令式累加器直接照搬到 Scala 中。
- `ScheduleWindow` 需要正确处理跨午夜窗口。
- 告警路由要综合考虑严重级别、标签覆盖、当前排班窗口、升级通道和 fallback 目标。
- 告警在 after-hours 且策略要求压制时，要改走 fallback 通道，并只生成一条 digest 式升级步骤。
- `AlertRouter` 需要支持单条和批量路由。
- `summarizeByChannel` 要统计所有升级步骤按通道聚合后的数量。
- `escalationTargets` 要返回单个路由决策中涉及到的去重目标列表，并保持首次出现顺序。
- 代码必须能通过 Scala 2.13 编译，并通过测试直接运行。

除了通过测试，也请让代码本身保持清晰、可读、易维护。
