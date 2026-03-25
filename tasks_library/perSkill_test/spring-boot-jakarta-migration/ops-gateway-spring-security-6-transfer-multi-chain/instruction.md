`/workspace` 里是一个已经升级到 Java 21 与 Spring Boot 3 的运维网关服务，但安全配置文件 `src/main/java/com/example/opsgateway/security/GatewaySecurityChains.java` 仍然保留旧版多适配器写法，当前工程无法在现有依赖下通过构建与验证。

请把这个文件改造成按顺序生效的多个组件式安全链，并保持下面这些接口语义：

1. 使用多个 `SecurityFilterChain` Bean 取代旧的继承式安全配置，分别覆盖公开入口、内部运维入口和 API 入口。
2. `/actuator/health` 与 `/docs/**` 必须允许匿名访问。
3. `/internal/**` 必须继续使用 HTTP Basic，并且只有 `OPS` 角色可以访问。
4. `/api/**` 必须继续走无状态鉴权，请保留现有 bearer token 过滤器接入方式。
5. 发往 `/api/**` 的 Basic 认证请求不能被当作有效 API 访问。
6. 使用 `requestMatchers` 配置 URL 规则，不再依赖旧版匹配方式。
7. `/docs/index.html` 继续允许匿名访问，且响应页面中必须保留 `Gateway Runbook` 文案。
8. 成功访问 `/internal/ops/status` 时，响应 JSON 需要继续包含 `surface: "internal"`，并让 `principal` 反映通过 Basic 认证的用户名；使用现有 `opsbot / ops-pass` 凭据访问时，`principal` 应为 `opsbot`。
9. 成功访问 `/api/v1/transfers` 时，响应 JSON 需要继续包含 `surface: "api"`、`mode: "stateless"`，并保持现有 bearer token 语义，即 `Bearer ops-api-token` 会认证为 `api-robot`，因此 `principal` 应为 `api-robot`。
10. `mvn test` 必须通过，并且服务启动后应满足上述接口行为。

除非确有必要，不要改动接口路径、现有过滤器逻辑、测试代码或任务目录结构。
