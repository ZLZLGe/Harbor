`/workspace` 下是一个已经切到 Spring Boot 3 的报表聚合服务。当前日报功能的业务结果本来应该正确，但升级后由于查询抓取策略写得不合适，出现了两类回归：

- 同一运单在报表里会重复出现。
- 生成日报时触发了额外 SQL，性能明显退化。

请修复这些兼容性与性能问题，并确保 `mvn test` 通过。主要改动应落在 `/workspace/src/main/java/com/example/reporting/service/ShipmentSummaryService.java`，如有必要可以调整少量配套代码。

需要满足的行为契约：

1. `loadDailyShipmentSummaries(LocalDate reportDate)` 只返回 `departureDate = reportDate` 且 `status` 属于 `IN_TRANSIT`、`DELIVERED` 的运单。
2. 返回结果中每个运单只能出现一次，即使该运单包含多条明细行也不能重复。
3. 结果必须按运单号升序排列。
4. 每条汇总结果都必须包含正确的 `referenceNumber`、`warehouseCode`、`customerName`、`lineCount`、`totalUnits`、`priority`。
5. 测试会通过 Hibernate statistics 统计 SQL 预处理语句数量；生成当天报表时，查询次数必须控制在不超过 2 次。
6. 允许通过合适的抓取策略、查询改写或实体图来修复问题，但不要改变现有对外方法签名。

完成后请自行运行：

```bash
mvn test
```
