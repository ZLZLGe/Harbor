`/workspace` 下有一个非 Web 的账单归档批处理程序，已经切到 Spring Boot 3，但归档逻辑仍残留 Hibernate 5 时代的写法，导致当前项目在 Hibernate 6 下无法稳定工作。

请修复兼容性问题，并确保 `mvn test` 通过。主要改动应落在 `/workspace/src/main/java/com/example/billing/job/InvoiceArchiveJob.java`，同时把与主键生成相关的遗留写法一并迁移到当前栈兼容的实现。

需要满足的行为契约：

1. `archiveOverdueInvoices(LocalDate businessDate)` 只归档 `status = SENT`、`dueDate` 早于 `businessDate`、且 `archived = false` 的账单。
2. 每次归档后，匹配账单都必须更新为 `archived = true`，并写入统一的 `archivedAt` 时间戳。
3. 每一张本次归档的账单都必须新增一条审计记录，记录对应账单号、`reason = "OVERDUE"`、`operator = "billing-batch"`，并复用同一归档时间戳。
4. 已支付、未逾期、已归档的账单都不能被修改，也不能生成新的审计记录。
5. 返回结果需要包含本次归档的账单数量、审计写入数量，以及按账单号升序排列的归档账单号列表。
6. 移除遗留的 Hibernate 5 专属旧式 Criteria API、修正旧的 bulk HQL 写法，并把过时的主键生成策略迁移为当前兼容方案。

完成后请自行运行：

```bash
mvn test
```
