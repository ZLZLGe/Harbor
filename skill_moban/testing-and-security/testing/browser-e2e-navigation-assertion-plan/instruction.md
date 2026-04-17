你需要根据浏览器导航流用例生成一份 E2E 导航断言规划表。

输入文件位于 `/app/workspace/input/browser_flow_cases.csv`，字段包括：
`flow_id,needs_network_assertion,prefetch_visible,expects_cache_hit,criticality,uses_wallet,known_flaky`
以及可选的 `response_token`。

请生成输出文件 `/app/workspace/output/e2e_navigation_plan.csv`，列顺序必须严格固定为：
`flow_id,assertion_mode,link_strategy,pom_required,artifact_policy,flake_mitigation,priority`

规则要求：

- 按 `flow_id` 升序排序。
- 如果 `expects_cache_hit=true`，优先使用 `no-requests` 作为 `assertion_mode`。
- 如果需要做网络响应断言，使用 `includes:<token>` 形式，其中 `<token>` 来自输入中的 `response_token`。
- 如果可见预取会带来不稳定性，应使用隐藏链接或 accordion 方案。
- 对复杂或关键流程要求页面对象模型（POM）。
- 对关键或已知不稳定流程使用更严格的 artifact 捕获策略。
- 只有在 `known_flaky=true` 时才允许使用隔离/隔离队列（quarantine）。
- 不要输出额外列。
- 不要输出空字符串、`null`、`N/A`、`None` 等空值占位。

可使用离线、确定性的方式完成该任务。
