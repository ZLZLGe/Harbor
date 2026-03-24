`/workspace` 里是一个已经升级到 Java 21 和 Spring Boot 3.2 的告警桥接服务。当前遗留问题集中在 [`src/main/java/com/example/incident/client/IncidentBridgeClient.java`](/workspace/src/main/java/com/example/incident/client/IncidentBridgeClient.java)：它仍然依赖旧式同步 HTTP 客户端和自定义 `ResponseErrorHandler` 与外部事件源交互。

这个客户端负责两类出站请求：

1. `pollEvents` 发送 `GET /incident-feed/events`，携带 `serviceName`、`batchSize`，以及仅在 `sinceToken` 非空时才发送的 `sinceToken` 查询参数，用来轮询新的告警事件。
2. `createFollowUpTicket` 发送 `POST /incident-feed/follow-up-tickets`，把事件跟进工单请求作为 JSON 请求体提交出去。

请把这个客户端迁移为 Spring 6.1 推荐的 fluent HTTP 客户端实现，并满足下面约束：

1. 保留共享的 base URL 配置。
2. 保留默认 JSON 请求头配置。
3. 不要改变公开方法签名，也不要修改现有 DTO 和领域异常类型。
4. 使用状态处理链把 `404`、`429` 和 `5xx` 分别映射为现有的 `IncidentFeedMissingException`、`IncidentRateLimitedException` 和 `IncidentBridgeServerException`。
5. `429` 仍需保留 `Retry-After` 头中的秒数，并写入 `IncidentRateLimitedException`。
6. 保持现有的事件抓取与工单创建请求语义不变。
7. 让 `mvn clean compile` 和 `mvn test` 通过。

这个任务的主要输出文件是：

- `/workspace/src/main/java/com/example/incident/client/IncidentBridgeClient.java`
