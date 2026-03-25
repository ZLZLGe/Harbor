这是一个 Spring Boot 现代化迁移任务。

`/workspace` 下是一套遗留理赔 REST 微服务，当前基于 Java 11 与 Spring Boot 2.6。它提供理赔创建与查询接口，带有基于 JWT 的鉴权、方法级权限控制、JPA 持久化、参数校验，以及对外部风控服务的 HTTP 调用。

你的目标是在不改变现有 REST 行为语义的前提下，把它升级到 Java 21 和 Spring Boot 3.2，并让代码与测试全部通过。

必须完成的迁移结果：

1. 把 Maven 构建升级到 Java 21 与 Spring Boot 3.2.x，清理与新版本冲突的旧依赖。
2. 将应用源码中的 `javax.*` 迁移为 Boot 3 兼容的 `jakarta.*` 命名空间。
3. 将旧式 `WebSecurityConfigurerAdapter` 安全配置改造成 Spring Security 6 写法，但保持以下访问语义不变：
   - `GET /api/public/health` 仍然允许匿名访问。
   - `GET /api/claims/{id}` 仍然要求已认证用户访问。
   - `POST /api/claims` 仍然只允许 `ADJUSTER` 角色访问。
4. 将旧版 `jjwt` 0.9 升级到可在 Java 21 / Spring Boot 3.2 下工作的版本与用法。
5. 将基于 `RestTemplate` 的风控调用迁移为 Spring Boot 3.2 兼容的 HTTP 客户端写法，例如 `RestClient` 或 `WebClient`。
6. 运行并通过：
   - `mvn clean compile`
   - `mvn test`

主输出文件是：

- `workspace/src/main/java/com/acme/claims/config/SecurityConfig.java`

你可以修改 `/workspace` 内的任意项目文件，只要最终行为契约和上述构建结果满足要求即可。
