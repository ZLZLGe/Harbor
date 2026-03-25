你需要修复一个 Next.js 运维指挥台的服务端性能问题。这个任务可以直接使用已提供的 shipped skill。当前 `/control-room` 页面会为每个面板重复请求同一份操作员会话，并把多个上游面板串行等待；事件确认接口也有不必要的串行依赖，导致整页和确认动作都明显超时。主要输出文件是 `src/lib/getControlRoomData.ts`。

主要目标：

- 让 `/control-room` 在保留现有面板结构、测试标记并继续展示上游返回内容的前提下完成服务端优化。
- 消除一次页面请求里的重复会话鉴权，并把独立面板改成并行取数。
- 缩短 `POST /api/events/[eventId]/confirm` 的依赖链，让确认动作继续走真实上游，但不要被非关键步骤阻塞。

必须保持可工作的行为：

- `/control-room` 必须继续展示操作员信息、Incident feed、Service health、Deployment lane 和 Approval queue。
- 页面里的这些 `data-testid` 必须保留：`operator-chip`、`incident-feed`、`service-health`、`deployment-lane`、`approval-queue`。
- `POST /api/events/evt-204/confirm` 必须继续返回 JSON，并至少包含 `eventId`、`status`、`confirmedBy`、`runbookId` 和 `timelineMessage`。
- 不要把接口改成硬编码静态返回，也不要绕过 `EXTERNAL_API_URL` 指向的上游。

性能预算：

- 预热后再次请求 `/control-room` 应在 1050ms 内返回，同时仍然慢于 650ms，证明真实上游仍在执行。
- 对于一次 `/control-room` 请求，上游诊断统计里的 `session` 必须只有 1 次，同时 `incidents`、`serviceHealth`、`deployments`、`approvals` 都必须各为 1 次。
- `POST /api/events/evt-204/confirm` 应在 1100ms 内返回，同时仍然慢于 650ms。
- 对于一次确认请求，上游诊断统计里的 `session`、`policy`、`prepare`、`confirm` 都必须各为 1 次。

约束：

- 不要修改或删除现有 `data-testid`。
- 不要移除任何现有上游调用，只能重组调用顺序、共享结果或让非关键步骤不阻塞响应。
- `src/lib/getControlRoomData.ts` 里已经有当前页面和确认接口共用的数据流；优先在这个文件里完成修复。

调试辅助：

- 容器内提供了诊断端点 `http://localhost:3001/_diagnostics/reset` 和 `http://localhost:3001/_diagnostics/stats`，可以用来观察一次请求触发了多少次上游调用。
