# Fulfillment Exception Reconciliation

这个模板面向 `ecommerce` 类 skill 任务，目标是做一个更接近真实运营诊断流的电商履约对账任务。它综合参考 SkillsMP ecommerce 类热门 skill 的共性能力：订单查询与状态排查、跨平台商品 / 价格 / 评论采集、Shopify / 多平台店铺管理、库存与销售订单管理、物流面单与 tracking、SKU / catalog 匹配、销售运营 workflow。任务设计不追求绑定单一平台，而是抽象出“多来源业务事实收集 -> 规则对齐 -> 异常判断 -> 正式交付”的通用流程。

## 第一部分：任务设计参考

* **Skill 价值定位**：技能收益必须体现在把电商任务里的重复性、高出错操作流程化，例如识别平台和数据源、拉取订单 / 商品 / 库存 / 物流状态、统一 SKU / variant / tracking / customer 等关键 ID、对齐业务规则并生成可审计输出。严禁让 skill 直接携带固定答案、绕过真实 API / 本地服务，或只包装一个吐出最终报告的黑盒脚本。
* **任务目标形态**：任务应要求 Agent 完成一个端到端电商运营问题，而不是单点工具调用。比较通用的设计流程是：读取冻结业务配置和样本数据 -> 调用当前店铺 / 仓储 / 物流 / marketplace 服务 -> 汇总多来源事实 -> 识别异常或生成运营决策文件 -> 输出 CSV / JSON / report 等正式交付物。不应设计成纯静态文件转换、简单 CRUD、只改前端页面、只考平台文档记忆，或没有跨来源对账压力的任务。
* **验证设计重点**：Verifier 要自己从服务和输入数据里重新算一遍结果，不能只看文件是否存在。重点检查 Agent 是否真的查过订单、库存、物流等服务，输出里的数量、异常类型和证据是否对得上。还要防止硬编码旧答案、只用过期快照、改输入数据或伪造服务调用记录。

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
