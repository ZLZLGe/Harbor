订单分析服务位于 `/workspace/order-analytics`。当前列表页会先查出订单，再为每一条订单分别读取客户层级、配送状态和订单统计，数据量上来后会形成明显的查询风暴，接口经常在高峰时段超时。

请重构 `/workspace/order-analytics/src/main/java/com/acme/analytics/reporting/OrderSummaryQueryService.java`，要求如下：

1. 保留公开类型以及 `fetchOrderSummaries(...)` 的返回契约，不要改动输出语义。
2. 将逐单查询改成批量聚合读取，显著减少仓储调用次数。
3. 列表行内容和 `totals` 必须继续保持正确，缺少发货记录的订单仍要返回 `PENDING`。
4. 完成后确保项目可以在 `/workspace/order-analytics` 下通过：

```bash
cd /workspace/order-analytics
mvn -q -DskipTests package
```

验证器会检查：

- 返回结果与 totals 是否仍然正确；
- 查询路径是否已经收敛，不再对每条订单触发多次单条仓储查询；
- 主要输出文件是否仍为 `/workspace/order-analytics/src/main/java/com/acme/analytics/reporting/OrderSummaryQueryService.java`。
