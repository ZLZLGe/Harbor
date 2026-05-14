# Payment Template

这是面向 `payment` 类 skill 的模板。它综合参考 SkillsMP `payment` 类热门 skill 的共性能力：订阅续费批次处理、金额计算、失败支付分流、按量计费收口、税额处理，以及把批处理结果稳定写成结构化交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`payment` 类热门 skill 的共同价值，是把 plan catalog、subscription state、invoice state、usage rollup、current-cycle change 和 policy 组织成可执行的账单处理流程。高质量 skill 不应代替 solver 交付结果，而应帮助 solver 更快完成金额口径统一、动作优先级判断和批处理回放校验。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否完成了账单动作和金额逻辑，而不是只卡格式。重点应覆盖 licensed 与 metered 金额合并、current-cycle adjustment、manual invoice / retry / payment-method / exhausted collection 的动作优先级，以及 replay 与 shadow run 下的行为一致性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`payment__renewal-batch-processor`
- 类别：`payment`
- 绑定 Skill：`billing-automation`
- 输入数据参考来源：
  - `environment/data/plan_catalog_seed.json`：任务内产品与价格目录；设计形态参考 Stripe sample seed 与 Price object  
    https://raw.githubusercontent.com/stripe-samples/checkout-single-subscription/main/sample-seed.json  
    https://docs.stripe.com/api/prices/object
  - `environment/data/subscription_snapshot.ndjson`：任务内订阅快照；字段语义参考 Stripe Subscription object  
    https://docs.stripe.com/api/subscriptions/object
  - `environment/data/invoice_snapshot.ndjson`：任务内发票快照；字段语义参考 Stripe Invoice object  
    https://docs.stripe.com/api/invoices/object
  - `environment/data/change_requests.csv`：任务内套餐与数量变更请求；规则形态参考 Stripe Prorations  
    https://docs.stripe.com/billing/subscriptions/prorations
  - `environment/data/usage_rollups.csv`：任务内按量计费汇总；规则形态参考 Stripe Usage-based billing  
    https://docs.stripe.com/billing/subscriptions/usage-based
  - `environment/data/billing_policy.yaml`：任务内 retry、pause 和 tax 规则；规则形态参考 Stripe Smart Retries 与 Tax for subscriptions  
    https://docs.stripe.com/billing/revenue-recovery/smart-retries  
    https://docs.stripe.com/tax/subscriptions

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 格式要求 | 检查最终输出（CSV / JSON）是否齐全、可读，且满足规定字段与操作类型要求 | 保证批量处理结果格式规范、随时可交付 |
| 计费逻辑验证 | 结合产品目录、实际使用量、变更记录和业务规则，重新核定每个订阅的续费、调整、税费和未结金额 | 统一固定套餐、按量计费、费用调整和税费的计算标准 |
| 账单动作验证 | 根据发票、支付方式、收款渠道和规则，重新判定当前应采取的账单操作及原因 | 正确落实扣款重试、人工开票、暂停服务和监控观察的优先级 |
| 结果闭环 | 核对账单操作总数、冻结订阅数和金额汇总是否与明细数据完全一致 | 确保明细报表与汇总结论完全对齐 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 数据目录保护 | 原始数据文件（`/root/data/`）不允许被篡改 |
| 执行结果验证 | 重新运行主程序（`/root/app/main.py`），生成的结果必须与提交记录完全吻合 |
| 动态数据校验 | 在随机副本中修改使用量和审核通过的额度，要求系统自动计算出的金额也能随之准确更新 |
| 产出物限制 | 输出目录（`/root/output/`）中只能包含题目明确要求交付的文件 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 plan catalog、renewal target、current-cycle adjustment、metered usage 和动作路由整理成一条更稳定的批处理实现链路，并把批量核查脚本与 replay 思路前置，减少在动作优先级和证据字段上的反复试错。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `2/3` | 近 3 次有效对照里，without Skill 持续遗漏动作路由或证据字段关键点；with Skill 有更高通过率。 |
| Agent 执行耗时 | `304.4s` | `211.4s` | With Skill 的收敛更快，平均 Agent 耗时降低约 `30.6%`。 |
| Tokens | `403373` | `299332` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.35x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   └── skills/
├── tests/
└── solution/
```
