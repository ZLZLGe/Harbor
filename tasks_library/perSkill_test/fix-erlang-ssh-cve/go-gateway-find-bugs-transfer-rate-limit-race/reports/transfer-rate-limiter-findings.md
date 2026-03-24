# Transfer - 审计 Go 租户限流器重构

## 审计范围

- 仓库：`/home/levi/Harbor/codex_task_builder_runs/scratch/20260319193954-fix-erlang-ssh-cve-find-bugs-sfgy4m/fix-erlang-ssh-cve/drafts/go-gateway-find-bugs-transfer-rate-limit-race/environment/workspace/gateway-review`
- 基线分支：`main`（`b53a1cc`）
- 审计分支：`levi/tenant-limiter-refactor`（`707bced`）
- 已完整阅读文件：
  - `docs/review-brief.md`
  - `internal/gateway/tenant_middleware.go`
  - `internal/limiter/tenant_limiter.go`
  - `internal/limiter/tenant_limiter_test.go`

## 已确认问题

### 1. High - 请求路径上的异步清理与 `tenants` map 无锁并发访问

- 位置：`internal/gateway/tenant_middleware.go:31`、`internal/gateway/tenant_middleware.go:34`、`internal/limiter/tenant_limiter.go:43`、`internal/limiter/tenant_limiter.go:58`、`internal/limiter/tenant_limiter.go:68`、`internal/limiter/tenant_limiter.go:92`、`internal/limiter/tenant_limiter.go:99`
- 问题：分支把清理逻辑放回请求路径，在 `AllowTenant()` 里每次请求后直接起 goroutine 调 `CleanupIdleTenants()`。但 `TenantLimiter` 里的 `tenants` 只是普通 map，`bucketFor()` 会在请求主路径读写它，`CleanupIdleTenants()` 会在异步 goroutine 里遍历并删除它，整个重构没有任何互斥或串行化。
- 证据：`tenant_middleware.go:31-35` 先调用 `Allow()`，再立即 `go m.limiter.CleanupIdleTenants(...)`；`tenant_limiter.go:58-69` 在 `bucketFor()` 中按 tenant 读写 `l.tenants`，`tenant_limiter.go:92-99` 在清理路径上遍历并 `delete(l.tenants, tenant)`。这正好形成 Go 运行时最典型的 “concurrent map read and map write / concurrent map iteration and map write” 风险。
- 影响：只要并发请求同时命中新 tenant 创建、旧 tenant 复用和异步清理，就可能直接触发 panic，或者在未启用 race detector 时出现桶状态丢失、限流决策抖动等不确定行为。对 API gateway 来说，这已经是可由外部流量触发的稳定性问题。
- 覆盖缺口：现有测试只有 `TestSerialRequestsStayTenantScoped`、`TestCleanupKeepsBusyTenant` 和 `TestCleanupDropsIdleTenant` 三个串行单测，没有任何并发请求场景，也没有 `go test -race` 或针对 `Allow()+CleanupIdleTenants()` 交错执行的覆盖。

### 2. High - 被限流请求会永久抬高 `inflight` 计数，清理失效并放大租户桶资源耗尽

- 位置：`docs/review-brief.md:12`、`internal/limiter/tenant_limiter.go:49`、`internal/limiter/tenant_limiter.go:51`、`internal/limiter/tenant_limiter.go:64`、`internal/limiter/tenant_limiter.go:68`、`internal/limiter/tenant_limiter.go:74`、`internal/limiter/tenant_limiter.go:77`、`internal/limiter/tenant_limiter.go:81`、`internal/limiter/tenant_limiter.go:96`
- 问题：`Allow()` 先执行 `atomic.AddInt64(&bucket.inflight, 1)`，然后才做真正的令牌判定；一旦请求被限流，函数在 `tenant_limiter.go:77-79` 直接返回，根本不会走后面的异步减计数逻辑。与此同时，`bucketFor()` 会无条件给每个新 tenant 建桶并放进 map，而文档还明确宣称“不再需要 global tenant cap”。
- 证据：`tenant_limiter.go:64-69` 对新 tenant 总是分配并保存 bucket；`tenant_limiter.go:74-84` 里只有通过限流检查的请求才会在 goroutine 中把 `inflight` 减回去；`tenant_limiter.go:96` 的清理条件又要求 `inflight == 0` 才允许删除。结果就是，攻击者只要对某个 tenant 连续打到第一次被拒绝，该 tenant 的 `inflight` 就会永久卡在正数，后续清理永远跳过它。再结合可控的 tenant ID，这个 map 可以被外部请求持续撑大。
- 影响：这不是单纯的 metrics 漂移。泄漏的 `inflight` 会让“空闲 tenant 自动回收”机制失效，攻击者可以用大量随机 tenant ID 或对每个 tenant 做一次 over-limit 请求，把 bucket 永久钉在内存里，最终放大为可利用的内存/GC 压力问题。
- 覆盖缺口：当前测试只验证首个请求通过、忙碌 tenant 不被立即清理、以及成功请求在延迟后可以被清理；没有任何用例覆盖“被拒绝请求之后 `inflight` 是否回落”或“大量 tenant ID 是否仍然有边界”。

## 已检查但未发现新增问题

- `tenantFromRequest()` 仍然只从 `X-Tenant-ID` 读取并做空白裁剪，串行路径下不同 tenant 的令牌桶隔离语义还在。
- `tokenBucket.allow()` 的令牌补充和扣减逻辑没有在这次 diff 中被改坏；单线程 happy path 下基本限流行为仍与基线一致。
- `SweepIdle()` 这个同步入口本身没有额外绕过条件，核心问题出在请求路径新增的异步清理和 `inflight` 泄漏，而不是清理 API 完全缺失。

## 核查清单

- 输入面：确认外部可控输入主要是请求头里的 tenant ID，以及请求到达时机带来的并发交错。
- 共享状态：重点核查了 `tenants` map、每个 bucket 的 `inflight` 和 `lastSeenUnix`，确认它们都在请求路径上被共享访问。
- 竞态：已确认 1 条真实存在的 map 并发访问问题。
- 计数失真 / 资源消耗：已确认 `inflight` 泄漏会直接阻断回收，并与取消 tenant cap 的设计叠加，形成可放大的资源耗尽面。
- 测试覆盖：现有分支测试只覆盖串行 happy path，没有覆盖并发或拒绝路径。

## 无法完全验证的部分

- 我没有在这个环境里跑并发压测或 `go test -race`，所以没有给出具体触发 panic 的请求序列和内存曲线。
- 不过基于 `main...HEAD` 的完整 diff、共享状态访问方式和测试缺口，上述两个问题已经能在静态审计层面确认成立，不依赖额外推测。
