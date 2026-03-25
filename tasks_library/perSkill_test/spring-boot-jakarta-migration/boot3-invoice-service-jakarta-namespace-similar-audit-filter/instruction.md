在 `/workspace` 下有一个已经切到 Java 21 与 Spring Boot 3 的发票审计服务，但一次不完整的迁移把部分源码和测试辅助类留在了旧命名空间上，导致当前 `mvn test` 无法通过。

请修复这次迁移，重点检查并更新这些位置：

- `src/main/java/com/example/invoice/domain/InvoiceRecord.java`
- `src/main/java/com/example/invoice/web/CreateInvoiceRequest.java`
- `src/main/java/com/example/invoice/web/AuditTrailFilter.java`
- `src/test/java/com/example/invoice/support/CapturingFilterChain.java`
- 以及与这些文件直接相关、仍残留相同问题的 Java 文件

需要满足的结果：

1. 项目中与本次任务相关的 `javax.persistence`、`javax.validation`、`javax.servlet` 引用都要迁移到 Spring Boot 3 可用的命名空间。
2. `AuditTrailFilter` 需要继续保留当前业务语义：
   - 读取请求头 `X-Actor`
   - 空白或缺失时回退为 `anonymous`
   - 把 actor 写入请求属性 `audit.actor`
   - 把 `METHOD:URI:actor` 写入响应头 `X-Audit-Trace`
3. 最终 `mvn test` 必须通过。

不要重写成其他技术栈，也不要绕开现有测试语义。
