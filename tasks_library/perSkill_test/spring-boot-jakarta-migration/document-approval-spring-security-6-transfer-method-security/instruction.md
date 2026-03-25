`/workspace` 里是一个已经升级到 Java 21 与 Spring Boot 3 的文档审批服务，但安全配置文件 `src/main/java/com/example/approval/security/MethodSecurityConfiguration.java` 还停留在旧版写法，导致方法级授权和最小化的请求放行规则都失效了。

请只围绕这个安全配置文件完成迁移，并保持现有业务与测试语义：

1. 使用组件式配置，不再依赖旧的继承式安全配置。
2. 启用方法级鉴权，现有服务层 `@PreAuthorize` 规则必须继续生效。
3. 使用 `requestMatchers` 配置请求规则，不再使用旧版 URL 匹配 API。
4. `POST /api/session/login` 必须允许匿名访问。
5. `/actuator/health` 必须允许匿名访问。
6. 除上面两个公开入口外，其余请求都必须要求认证。
7. `mvn test` 必须通过。

除非确有必要，不要改动测试代码、接口路径或任务目录结构。
