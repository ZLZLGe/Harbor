# Backend Template

这是面向 `backend` 类 skill 的模板。它综合参考 SkillsMP backend 类热门 skill 的共性能力：REST API 契约设计、资源建模、状态码语义、错误 envelope、分页过滤、鉴权授权、rate limiting、幂等创建、微服务网关和下游故障映射。

## 第一部分：任务设计参考

* **Skill 价值定位**：backend 类 skill 的核心价值，是把接口实现从 happy path 提升到生产级 HTTP 契约和运行时行为。模板任务应让 skill 在资源路径、请求校验、响应 envelope、错误语义、幂等性、鉴权隔离、限流和下游 resilience 上降低遗漏率，而不是靠静态 mock 或隐藏答案通过。
* **Task目标形态**：任务应要求 Agent 在真实本地服务链路中补齐 backend API、gateway、controller、middleware 或 service 层行为，并通过真实 HTTP 请求验证。目标形态适合设计成 REST facade、微服务编排、分页列表、资源创建/读取、幂等 replay、权限隔离和故障降级，不适合做静态 JSON 输出、纯算法题或只修一个 typo。
* **Verifier设计重点**：Verifier 应通过运行中的服务和真实 HTTP 请求检查行为结果，并验证下游 ledger 或副作用证明 gateway 确实调用依赖服务。重点应覆盖输入不可变、契约 schema、状态码、rate-limit headers、cursor pagination、idempotency、resource ownership、validation errors、502/503 映射和防绕过下游服务。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`backend__partner-shipping-api-contract`
- 类别：`backend`
- 难度：`hard`
- 绑定 Skill：`api-design`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 在同一个单容器环境中启动 gateway、carrier rate service 和 shipment booking service，通过真实 HTTP 请求独立验证 quote/list/create/read 全链路。它关注 API 行为、契约语义、下游副作用和故障映射是否正确，而不是实现文件是否一致。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 认证失败、bad JSON、字段语义错误和统一 error envelope | HTTP 状态码语义、请求校验和错误契约 |
| `GET /shipping-quotes` filtering、sorting、cursor pagination、`links.next` | REST list contract、分页、过滤和稳定响应 envelope |
| partner capability 过滤与显式不允许能力返回 `403` | 鉴权授权、资源能力隔离和安全响应 |
| `POST /shipments` 的 `201 Location`、idempotent replay、idempotency conflict | 幂等创建、资源创建契约和冲突语义 |
| `GET /shipments/:id` owner isolation 与 missing/foreign 统一 `404` | 资源所有权隔离和信息泄漏防护 |
| `429`、`Retry-After`、`X-RateLimit-*` headers | 生产 API rate limiting 和 header contract |
| rate/booking downstream ledger 与 502/503 failure-mode switching | 微服务 gateway、真实下游调用和 resilience 映射 |
| data/contracts/services hash guardrail | 输入不可变、防静态 mock 和反绕过测试 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 public REST API 的生产契约系统化：资源路径、状态码、统一错误 envelope、cursor pagination、幂等创建、资源隔离、rate-limit headers 与 502/503 下游语义。without Skill 也理论可解，但更容易漏掉 shipment response contract、rate-limit headers 或边界状态码。

基于最近 **7** 次有效 task-level 实验（均跑到 verifier；已排除 `BuildException` / `ConnectError` 启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `33.3%` | `75.0%` | without Skill 两次失败，主要漏 shipment response contract 与 rate-limit header/错误语义；with Skill 通过率更高。 |
| Agent 执行耗时 | `541.3s` | `456.4s` | With Skill 平均 Agent 耗时降低约 `15.7%`。 |
| Tokens | `1.28M` | `0.84M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.53x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   │   ├── contracts/
│   │   ├── data/
│   │   ├── gateway/
│   │   ├── services/
│   │   └── run.sh
│   └── skills/
├── tests/
├── solution/
└── README.md
```
