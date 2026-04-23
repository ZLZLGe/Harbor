# Fulfillment Exception Reconciliation

这个模板面向 `ecommerce` 类 skill 任务，目标是做一个更接近真实运营诊断流的电商履约对账任务。它综合参考了 SkillsMP ecommerce 类里更热门的能力方向：

- `ordercli.md`：`361.8k` stars，订单查询与状态排查
- `shopify-expert.md`：`8.4k` stars，Shopify API / 运营排障
- `clawpify.md`：`4.2k` stars，Shopify GraphQL Admin API
- `easypost.md`：`4.2k` stars，物流追踪与 shipping state
- `catalog-sku-matcher-india.md`：`4.2k` stars，SKU / catalog 匹配

核心目标是让 solver 在单容器内完成一条真实风格链路：`commerce admin GraphQL -> warehouse reservations -> carrier tracking -> reconciliation outputs`。

## 📌 任务元数据

- 任务 ID：`ecommerce__fulfillment-exception-reconciliation`
- 类别：`ecommerce`
- 难度：`hard`
- 绑定 Skill：`commerce-fulfillment-recon`
- 主要交付物：
  - `/root/output/fulfillment_exceptions.csv`
  - `/root/output/order_reconciliation_summary.json`
- 环境形态：单容器，容器内启动隐藏的 commerce admin、warehouse、carrier 三段本地服务

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`8/8` 通过
- Job：`ecommerce-template-oracle-final`
- Trial：`task_oracle_e2b__Si6tsXb`
- Task checksum：`34c66019728397afb5d044714fec2f1df1b5a5a4d61008aeac4b55336b0c33e3`
- 时间：`2026-04-23T14:56:43Z` 到 `2026-04-23T14:57:30Z`

Verifier 策略：

- 主测：检查两个正式交付物存在、可解析、字段完整且 schema 合法。
- 主测：从 live commerce admin、warehouse、carrier 服务独立复算期望异常行，不依赖现成答案文件。
- 主测：检查 CSV 行级 issue、severity、summary totals、issue_counts 与 live recomputation 一致。
- 主测：允许不同实现产生不同的 `expected_action` 或 evidence 字段命名，只要行为结果和关键证据语义成立。
- 防作弊：检查 solver 在 verifier 之前确实访问过 live 服务链路，且包含 GraphQL 分页访问。
- 防作弊：检查 `/root/data/` 和隐藏服务文件哈希不变，防止篡改输入或替换真实链路。
- 防作弊：检查服务在 verifier 结束时仍健康，并确认 live-only 订单没有被 stale snapshot 漏掉。

多模态：

- 不适用（纯结构化文件与本地 API 交互任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这道题里，skill 的关键价值不是泄露答案，而是把三件高成本工作标准化：

- Shopify-like GraphQL 分页与 variant 解析；
- warehouse reservation / carrier tracking 的探针路径；
- 证据更完整的异常行生成方式。

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | With Skill 已稳定全通过；Without Skill 仍未出现通过，失败原因主要是异常证据字段不够完整 |
| 平均总耗时 | `425.9s` | `382.4s` | With Skill 更快，平均总耗时降低约 `10.2%` |
| 平均 Agent 执行耗时 | `266.0s` | `275.5s` | With Skill 略慢约 `3.6%`，但换来稳定通过 |
| 平均 Input Tokens | `423,575` | `1,035,107` | With Skill 上下文更长，主要来自 helper/skill 发现与使用开销 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
