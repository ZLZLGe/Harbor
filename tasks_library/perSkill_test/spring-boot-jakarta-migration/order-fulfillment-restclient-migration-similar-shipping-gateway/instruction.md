`/workspace` 里是一个已经升级到 Java 21 和 Spring Boot 3.2 的订单履约服务。当前遗留问题集中在 [`src/main/java/com/example/orders/integration/ShippingGatewayClient.java`](/workspace/src/main/java/com/example/orders/integration/ShippingGatewayClient.java)：它仍然沿用旧的同步 HTTP 调用方式。

这个客户端现在负责三类出站请求：

1. `fetchQuote` 发送 `GET /shipping/quotes`，并携带 `destinationZip`、`declaredValue` 查询参数。
2. `createShipment` 发送 `POST /shipping/shipments`，请求体与响应体都是 JSON。
3. `cancelShipment` 发送 `DELETE /shipping/shipments/{shipmentId}`，并携带 `reason` 查询参数。

请把这个客户端改成 Spring 6.1 推荐的 fluent HTTP 客户端实现，并满足下面约束：

1. 保留共享的 base URL 配置。
2. 保留默认 JSON 相关请求头配置。
3. 不要改变公开方法签名和现有请求语义。
4. 让 `mvn clean compile` 和 `mvn test` 通过。

这个任务的主要输出文件是：

- `/workspace/src/main/java/com/example/orders/integration/ShippingGatewayClient.java`
