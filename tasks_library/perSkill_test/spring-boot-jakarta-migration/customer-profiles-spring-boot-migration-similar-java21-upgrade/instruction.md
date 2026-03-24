`/workspace/customer-profiles/` 下有一个遗留客户档案 REST 服务，需要从 Java 11 / Spring Boot 2.7 迁移到 Java 21 / Spring Boot 3.2。

请完成下面这些事情，重点输出文件是 `/workspace/customer-profiles/pom.xml`：

1. 更新父 POM 到 Spring Boot 3.2.x，并把 `java.version` 升级到 `21`。
2. 把旧版单包 `io.jsonwebtoken:jjwt:0.9.x` 替换为拆分后的新依赖。
3. 移除遗留的 `javax.xml.bind` / `jaxb-api` 依赖。
4. 不要引入与任务无关的新模块或多余依赖。

完成后，下面两个命令都必须成功：

1. `mvn -f /workspace/customer-profiles/pom.xml clean compile`
2. `mvn -f /workspace/customer-profiles/pom.xml test`
