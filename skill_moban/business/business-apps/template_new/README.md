# Business-Apps Template

这是面向 `business-apps` 类 skill 的模板。它综合参考 SkillsMP `business-apps` 类热门 skill 的共性能力：业务系统事实核对、旧导出与当前状态对齐、动作分流、运营节奏控制、收入风险识别，以及把多来源业务事实沉淀成结构化交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`business-apps` 类热门 skill 的共同价值，是把 CRM、billing、ops policy、action queue 这类分散事实组织成稳定的运营决策流程。高质量 skill 不应直接给出答案，而应帮助 solver 更快识别权威事实源、数据漂移位置、动作优先级和交付物的收口方式。
* **Task 目标形态**：任务应落在接近日常收入运营、业务运营或内部系统核对的场景里，例如续费分流、回款跟进、账单批次核对、动作台账整理或指标驱动的运营控制。题面应重点交代交付合同、业务约束和禁止事项，把具体链路更多留给 skill 和 solver 自主识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了当前业务链路和关键动作，而不是只卡格式细节。重点应覆盖权威服务访问、分页完整性、细项子资源核对、动作唯一性、汇总一致性，以及对旧导出依赖、跳过 live chain、硬编码结果和篡改环境的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`business-apps__renewal-action-queue`
- 类别：`business-apps`
- 难度：`hard`
- 绑定 Skill：`billing-automation`
- 输入数据参考来源：
  - `environment/data/crm_export.csv`：任务内续费 cohort 与 CRM 字段快照；字段语义参考 Stripe Subscription object  
    https://docs.stripe.com/api/subscriptions/object
  - `environment/data/invoice_snapshot.ndjson`：任务内 invoice 与 dunning 状态快照；字段语义参考 Stripe Invoice object  
    https://docs.stripe.com/api/invoices/object
  - `environment/data/action_policy.yaml`：任务内动作分流规则与阈值；语义参考 Chargebee Dunning v2  
    https://www.chargebee.com/docs/payments/2.0/dunning/dunning-v2
  - `environment/data/contact_directory.csv`：任务内账户负责人和升级联系信息；为本模板自定义的本地运营输入，无单独公开来源

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解通过本地 `revops` service 拉取 manifest、cursor 分页 cohort、账户 detail、renewal preview 和 dunning facts，再结合本地 policy 重算唯一动作桶、工作台账、控制汇总和业务摘要。Oracle 关注的是完整操作链路和结果一致性，而不是某个实现文件名。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 CSV / JSON / Markdown 是否存在、可解析，并满足必需字段与枚举值 | 先理解正式交付物，再组织结构化输出 |
| live action 重算 | 基于当前 service 和 policy 重算每个账户的动作桶、动作原因和 next step | 权威事实源优先、动作唯一性、规则落地 |
| 汇总一致性 | 校验 action counts、账户总数、ARR 总额和流程阻塞账户列表与 worklist 行级结果一致 | 行级判断与控制汇总收口一致 |
| 业务摘要语义 | 检查摘要包含流程阻塞账户、最高金额扩容账户、最紧急催收账户和路由逻辑说明 | 面向运营方的可执行汇报 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| live chain 使用痕迹 | solver 必须在 verifier 前查询 manifest、完整 cohort 分页，以及每个账户的 detail / renewal preview / dunning facts |
| 输入与环境完整性 | `/root/data`、隐藏 service 和安装后的 skill 文件 hash 不得变化 |
| live-only 账户覆盖 | 较早导出中缺失的 live-only 账户不能在输出中丢失 |
| 服务健康度 | verifier 结束时本地 `revops` service 仍需健康 |

### ⚡ Skill 相关性评估

结论：相关。这个任务里，Skill 的核心价值是把 manifest 拉取、分页 cohort、逐账户 detail / renewal preview / dunning 扩展，以及唯一动作分流整理成一条更稳定的工作链路。当前剩余失败主要集中在 `workflow_blocked_account_ids` 的口径热点，但 with Skill 组仍明显优于 without Skill 组。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33%` | 近 3 次有效对照里，without Skill 不如 with Skill 原因：without Skill 主要败在多信号账户的动作优先级和 `workflow_blocked_account_ids` 汇总口径，尤其容易把 `ACC-105` 误判进阻塞名单，或把它从 `update_expansion_quote` 误判成采购升级动作。 |
| Agent 执行耗时 | `250.2s` | `178.5s` | With Skill 的平均 Agent 耗时降低约 `28.6%`，分流收敛更快。 |
| Tokens | `0.72M` | `0.31M` | Without Skill 的上下文与试错开销约为 With Skill 的 `2.36x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
