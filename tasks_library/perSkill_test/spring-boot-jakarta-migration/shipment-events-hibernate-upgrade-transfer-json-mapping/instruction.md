`/workspace` 下是一个已经升级到 Java 21、Spring Boot 3.2 和 Hibernate 6 的物流事件仓储服务。当前只剩事件实体还保留着 Hibernate 5 时代的旧式 JSONB 类型声明，导致项目无法在新的 ORM 版本下完成编译与持久化测试。

请修复 `src/main/java/com/acme/logistics/model/ShipmentEvent.java`，让以下行为恢复正常：

1. 事件元数据可以作为 JSON 列成功写入数据库。
2. 重新读取事件时，嵌套字段和数组内容能够完整保留。
3. 现有仓储与测试代码无需改动即可通过构建。

约束：

- 优先只修改上述实体文件；其余模型、仓储和测试已经围绕新的运行时准备好。
- 不要改变字段语义、表结构命名和现有公开方法。
- 完成后需要通过：
  - `mvn -q -DskipTests compile`
  - `mvn -q test`
