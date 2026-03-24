`/workspace` 里是一个已经升级到 Java 21 和 Spring Boot 3.2 的对账批处理项目。批任务在读取外部总账分页数据并回写确认结果时，仍然依赖旧式同步 HTTP 客户端。

当前需要处理的核心文件是 [`src/main/java/com/example/reconciliation/client/LedgerSyncClient.java`](/workspace/src/main/java/com/example/reconciliation/client/LedgerSyncClient.java)。这个客户端被批任务直接调用，负责两类出站请求：

1. `fetchEntries` 发送 `GET /ledger/entries`，并带上 `limit`、`ledgerDate`，以及仅在游标非空时才发送的 `cursor` 查询参数。
2. `submitConfirmations` 发送 `POST /ledger/entries/confirmations`，把一次对账运行生成的批量确认结果作为 JSON 请求体提交出去。

请把这个客户端迁移为 Spring 6.1 推荐的 fluent HTTP 客户端实现，并满足下面约束：

1. 保留共享的 base URL 配置。
2. 保留默认 JSON 请求头配置。
3. 分页读取必须继续正确解析泛型分页响应，不能把响应退化成原始类型。
4. 不要改变公开方法签名，也不要修改批处理任务和现有测试期望的请求语义。
5. 让 `mvn clean compile` 和 `mvn test` 通过。

这个任务的主要输出文件是：

- `/workspace/src/main/java/com/example/reconciliation/client/LedgerSyncClient.java`
