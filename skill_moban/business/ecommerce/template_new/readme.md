# Fulfillment Exception Reconciliation

这个模板面向 `ecommerce` 类 skill 任务，目标是做一个更接近真实运营诊断流的电商履约对账任务。它综合参考了 SkillsMP ecommerce 类里更热门的能力方向：订单查询与状态排查、Shopify / Admin API 运营排障、物流追踪、SKU / catalog 匹配、库存与销售运营工作流。代表性 skills 包括：

- `ordercli.md`：`361.8k` stars，订单查询与状态排查
- `apify-ecommerce.md`：跨平台商品、价格、评论与卖家数据采集
- `persona-sales-ops.md`：销售运营、客户沟通与 deal workflow
- `shopify-expert.md`：`8.4k` stars，Shopify API / 运营排障
- `clawpify.md` / Shopify Admin API 类 skills：Shopify GraphQL Admin API、商品、订单与履约链路
- `zoho-inventory.md`：库存、销售订单、采购、账单与 shipment 记录管理
- `easypost.md`：`4.2k` stars，物流追踪与 shipping state
- `catalog-sku-matcher-india.md`：`4.2k` stars，SKU / catalog 匹配

核心目标是让 solver 在单容器内完成一条真实风格链路：`commerce admin GraphQL -> warehouse reservations -> carrier tracking -> reconciliation outputs`。

## 第一部分：任务设计参考

* **Skill 价值定位**：技能收益必须体现在“把真实电商运营链路中的高成本排查步骤标准化”，例如分页拉取订单、解析 Shopify-like variant / SKU、比对 catalog 期望履约方、查询仓库 reservation、归一化 carrier status、生成可审计 evidence。严禁让 skill 直接泄露固定答案、内置最终异常清单、绕过 live service，或把任务退化成照抄 helper 输出。
* **任务目标形态**：任务应要求 Agent 面向一个运营截止时间前的真实问题，跨 `commerce admin -> warehouse -> carrier` 多系统收集证据，产出可给运营经理使用的结构化异常报告。Agent 必须处理分页、stale snapshot、SKU drift、库存占用、物流状态冲突、缺失 tracking 等组合问题；不应只做单文件 CSV 清洗、静态 JSON 转换、纯 UI 表单填写，或只调用一个 mock API 得到答案。
* **验证设计重点**：Verifier 应从 live services 和冻结输入独立复算期望结果，重点验证输出 schema、行级 issue code、summary totals、evidence JSON、GraphQL 分页访问、服务健康与输入哈希。Verifier 还应允许不同实现的 `expected_action` 和 evidence 字段命名，只要关键语义成立；同时拦截硬编码旧答案、篡改 `/root/data/`、修改隐藏服务、跳过分页、只用 stale snapshot、伪造 service log 等规避方式。
* **数据与环境设计**：输入应同时包含冻结 manifest、catalog export、stale platform snapshot、carrier status codebook，以及隐藏服务中的 live-only 变化。这样 skill 的价值来自“发现 snapshot 与 live state 的差异”，而不是来自访问外网或依赖不可复现的数据。
* **难度与迁移性**：模板适合生成 hard 级任务。相似任务可以迁移到 marketplace returns、subscription fulfillment、inventory rebalancing、B2B wholesale order exception、OMS / WMS reconciliation 等场景，但仍应保留跨系统证据链和可机器验证的正式交付物。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce__fulfillment-exception-reconciliation`
- 类别：`ecommerce`
- 难度：`hard`
- 绑定 Skill：`commerce-fulfillment-recon`
- 主要交付物：
  - `/root/output/fulfillment_exceptions.csv`
  - `/root/output/order_reconciliation_summary.json`
- 环境形态：单容器，容器内启动隐藏的 commerce admin、warehouse、carrier 三段本地服务

### 📊 验证与测试指标（Oracle & Verifier）

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

### ⚡ Skill 相关性评估

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

### 📁 标准目录结构说明

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
