`/workspace` 下是一个已经升级到 Java 21、Spring Boot 3.2 和 Hibernate 6 的离线对账批处理应用。当前只剩查询仓储仍在使用 Hibernate 5 时代已经移除的旧 Criteria 写法，导致批次检索功能无法编译。

请修复 `src/main/java/com/acme/reconcile/persistence/ReconciliationSearchRepository.java`，让以下行为恢复正常：

1. 按状态、币种、批次日期范围、最小差异金额、是否升级人工复核，以及关键字做组合筛选。
2. 返回稳定的分页结果，不能因为明细行匹配而出现重复批次。
3. 输出同一套筛选条件下的汇总结果，包括命中批次数和差异金额合计。

约束：

- 其余模型、测试和数据已经围绕 Hibernate 6 准备好，优先只修改上述仓储文件。
- 不要改变现有方法签名，也不要改动业务筛选语义。
- 完成后需要通过：
  - `mvn -q -DskipTests compile`
  - `mvn -q test`
