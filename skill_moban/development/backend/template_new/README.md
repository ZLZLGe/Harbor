# Backend 模板任务说明

本模板面向 `backend` 类任务，重点对齐 SkillsMP backend 分类里当前高相关、且高星的 `api-design` 与 `backend-patterns` 这类能力要求。参考页：`https://skillsmp.com/categories/backend`，其中 `api-design.md` 与 `backend-patterns.md` 当前均位于该分类前列。这个模板的目标不是让 solver 从零搭一个新服务，而是把 solver 放进真实后端故障现场，在真实链路、真实状态流转和真实业务约束都存在的前提下完成诊断与修复。

## 模板范式

1. 任务必须落在真实后端工作流里，优先做库存、订单、认证、查询、状态机、缓存一致性这类真实业务问题，不做靠隐藏答案文件取巧的 puzzle。
2. Instruction 只能给症状、业务约束和禁止事项，不能直接泄漏根因或修复路径。
3. 环境必须保留真实风格的上下游依赖。对 backend 任务，至少要有公开服务和同容器内真实下游链路，不能退化成纯静态函数题。
4. Verifier 只验行为结果，不绑定唯一实现。只要 API 契约、业务结果和真实链路一致，就应允许不同修复路径通过。
5. Hidden tests 要优先卡“更深一层的状态收敛”而不是只卡表层接口。例如本模板额外要求 TTL 到点后，本地 hold 状态也要自行收敛，而不是必须靠下一次读请求触发。
6. Guardrails 要能拦截后端常见伪修复：硬编码返回、短路下游、删除状态流转、改测试数据、把多实体逻辑写死成单路径。
7. 正式 with_skill / without_skill 对照里，唯一区别只能来自 `environment/skills/` 及对应 Dockerfile 复制逻辑，不能额外改题面、测试、数据或依赖。
8. Skill 的验收标准应是“标准化诊断路径并提高稳定通过率”，而不是只让任务快一点。

## 示例任务

## 📌 任务元数据

- 任务名：`inventory-hold-consistency-fix`
- 类别：`backend`
- 难度：`hard`
- 标签：`backend`, `api-design`, `backend-patterns`, `idempotency`, `inventory`, `distributed-systems`, `consistency`, `fastapi`, `sqlite`
- 绑定 Skill：`inventory-hold-debugging`

任务要求修复一个门店自提库存预占服务。Solver 需要在保留真实 localhost 下游 `inventory-ledger` 的前提下，修复幂等重试、hold 过期释放、可售库存查询、以及确认/取消订单的状态一致性问题。

环境是单容器实现，包含三部分：

- `workspace/checkout-api/`：待修复的公开服务代码与本地 SQLite 状态。
- `inventory-ledger/`：真实下游库存账本服务。
- `skills/inventory-hold-debugging/`：标准化 replay、ledger 探针和 local-vs-ledger 对比脚本。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- Pytest：`9 passed in 11.71s`

### 📊 Verifier 验证策略

#### 1. 幂等与一致性校验
- **幂等控制**：同一 `Idempotency-Key` 的请求，严禁在下游创建重复的库存预占（Reservation）。
- **状态恢复**：若本地 Hold 记录丢失但下游租约存在，同 Key 重试须自动恢复本地状态，禁止引发二次库存扣减。
- **数据隔离**：多门店、多 SKU 的混合操作序列中，须保持严格的数据隔离与全局状态一致性。

#### 2. 生命周期与过期流转
- **主动收敛**：TTL 到期后，本地 Hold 状态须自动流转为 `expired`，严禁依赖后续读请求被动触发。
- **资源释放**：Hold 记录过期必须立即释放对应库存，并解除对 `GET /api/v1/availability` 接口的阻塞。
- **边界拦截**：严格拦截已过期的 Hold 记录，严禁将其确认为有效订单。

#### 3. 防作弊与链路审计
- **环境冻结**：强校验下游 `inventory-ledger` 源码及初始种子数据哈希，确保未经篡改。
- **链路求证**：公开 API 成功响应的前提是必须产生真实的下游 Ledger 事件，严禁通过硬编码或短路绕过底层调用链。

数据质量：

- 基线数据来自冻结的门店库存快照 `inventory-hold-consistency-2026-04-16`，覆盖 `4` 组 `sku + location`。
- 输入数据由固定 seed 与冻结 replay 样本组成，保证 E2B 与本地验证一致。
- 数据路径位于 `environment/workspace/data/catalog/` 与 `environment/workspace/data/replay/`。
- 任务不依赖在线网页抓取，避免引入时效性噪音；真实性来自业务链路与状态约束，而不是外部网站实时数据。

多模态：

- 不适用（纯后端服务与 HTTP 行为任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是替 solver “直接给答案”，而是把最容易走弯路的诊断流程标准化：

- 先 reset 公开服务和真实 ledger。
- 再重放冻结请求序列，而不是靠手写零散 curl 碰运气。
- 然后对比 local holds、idempotency records 和 downstream ledger snapshot。
- 最后重点检查 expiry、terminal state 和 local-vs-ledger drift。

这使 solver 更容易发现“表面 API 看似正常，但本地状态没有自行收敛”的隐藏问题。没有 skill 时，任务理论上仍可解，但需要自己拼出 replay 路径、探针脚本和对账口径，收敛成本明显更高。

基于当前已完成、且可核验的最终 `9` 测 task-level trial（With Skill `4` 条，Without Skill `3` 条）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/4 = 75%` | With Skill 已出现稳定完整通过；Without Skill 仍未出现通过 |
| 最佳成绩 | `8/9` | `9/9` | Without Skill 的最佳样本仍被隐藏的 idle-expiry 收敛测试拦下 |
| 平均 Agent 执行耗时 | `767.1s` | `753.6s` | With Skill 略快，平均 Agent 执行耗时降低约 `1.8%` |

补充说明：

- 有效 With Skill trial：`backend-template-with-skills-e2b-20260416-r13`（`9/9`）、`backend-template-with-skills-e2b-20260417-r19`（`9/9`）、`backend-template-with-skills-e2b-20260417-r21`（`7/9`）、`backend-template-with-skills-e2b-20260417-r23`（`9/9`）
- 有效 Without Skill trial：`backend-template-without-skills-e2b-20260417-r12`（`7/9`）、`backend-template-without-skills-e2b-20260417-r13`（`7/9`）、`backend-template-without-skills-e2b-20260417-r16`（`8/9`）
- 口径说明：
  - 本轮统一只统计最终 `9` 测版本的完整 backend task-level trial，不混入早期 `7/7`、`8/8` 版本样本
  - `backend-template-with-skills-e2b-20260417-r23` 的 task-level `trial/result.json` 与 verifier 输出完整，因此仍计入有效样本；外层 job 收尾时被中断，不影响该 task-level 结果判定
  - 当前 provider 没有稳定回填 `agent_result.n_input_tokens`，所以本轮不把 token 均值作为主对比指标

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── inventory-ledger/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
