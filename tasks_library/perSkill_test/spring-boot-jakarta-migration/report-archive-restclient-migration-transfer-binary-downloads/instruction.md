`/workspace` 里是一个已经升级到 Java 21 和 Spring Boot 3.2 的报表归档服务。当前遗留问题集中在 [`src/main/java/com/example/reporting/client/ArchiveExportClient.java`](/workspace/src/main/java/com/example/reporting/client/ArchiveExportClient.java)：它仍然使用旧式同步 HTTP 客户端与外部报表归档网关交互。

这个客户端负责三类出站请求：

1. `downloadCsv` 发送 `GET /archive/exports/{exportId}/csv`，携带 Bearer 认证头，并把返回的 CSV 文本原样交给上游处理。
2. `downloadPdf` 发送 `GET /archive/exports/{exportId}/pdf`，同样携带 Bearer 认证头，并返回二进制 PDF 字节数组。
3. `confirmImport` 发送 `POST /archive/import-confirmations`，把导入确认 JSON 回传给归档网关，并解析确认响应。

请把这个客户端迁移为 Spring 6.1 推荐的 fluent HTTP 客户端实现，并满足下面约束：

1. 保留共享的 base URL 配置。
2. 不要改变公开方法签名，也不要修改现有 DTO。
3. Bearer 认证头必须继续出现在下载和确认回调请求里。
4. CSV 下载仍然返回文本，PDF 下载仍然返回 `byte[]`，不要把它们改成统一的 JSON 处理。
5. 确认回调请求的 URL、JSON 请求体和响应契约必须保持不变。
6. 让 `mvn clean compile` 和 `mvn test` 通过。

这个任务的主要输出文件是：

- `/workspace/src/main/java/com/example/reporting/client/ArchiveExportClient.java`
