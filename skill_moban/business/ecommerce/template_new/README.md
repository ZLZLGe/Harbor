# Ecommerce Template

这是面向 `ecommerce` 类 skill 的模板。它综合参考 SkillsMP ecommerce 类热门 skill 的共性能力：订单查询与状态排查、跨平台商品 / 价格 / 评论采集、Shopify / 多平台店铺管理、库存与销售订单管理、物流面单与 tracking、SKU / catalog 匹配、销售运营 workflow。任务设计不追求绑定单一平台，而是抽象出“多来源业务事实收集 -> 规则对齐 -> 异常判断 -> 正式交付”的通用流程。

## 第一部分：任务设计参考

* **Skill 价值定位**：ecommerce 类热门 skill 的共同价值，是把店铺运营、订单履约、商品目录、库存、物流、支付、评价、价格监控等高频流程转成稳定可执行的操作路径。好的 skill 应帮助 Agent 识别平台和权限边界，正确使用 API / CLI / 抓取工具，处理分页、ID 映射、状态口径、危险写操作确认和结果汇总，而不是携带固定答案或把最终交付物封装成黑盒输出。
* **任务目标形态**：任务应落在真实电商工作流中，要求 Agent 完成一个有业务闭环的运营交付，例如订单状态排查、库存同步、履约对账、SKU / listing 匹配、价格或评论分析、物流标签与 tracking、数字商品订单管理、店铺配置或 Shopify 扩展实现。题目应让 Agent 从多个来源收集事实、做判断并产出可验收文件或变更结果，不宜设计成纯静态转换、单表 CRUD、只背平台文档、只改 UI，或缺少跨实体对齐压力的任务。
* **验证设计重点**：ecommerce 类任务的 verifier 应优先验证 Agent 是否完成了真实业务链路，而不是只检查交付物格式。通用检查点包括订单、商品、SKU / variant、库存、物流、支付、客户或评价等关键实体是否能跨来源正确对齐，最终数量、状态、异常类型、业务动作和证据是否相互一致。防作弊设计应覆盖电商任务常见捷径，例如只依赖过期导出、硬编码少量热门记录、跳过分页或筛选条件、忽略当前状态、篡改输入数据或替换服务链路。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ecommerce__fulfillment-exception-reconciliation`
- 类别：`ecommerce`
- 难度：`hard`
- 绑定 Skill：`commerce-fulfillment-recon`

### 📊 验证与测试指标（Oracle & Verifier）

Oracle：oracle 按题面要求读取 manifest、catalog 和本地电商服务，完整执行订单分页、SKU / variant 对齐、仓储库存与物流状态核验，并生成标准交付物。它的作用是证明任务可解，并为 verifier 设计提供一条符合真实业务链路的参考实现。

Verifier 策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 检查正式交付物是否存在、可解析，字段和 schema 是否完整。 | 知道电商履约对账任务最终要交付哪些文件，以及异常行、汇总统计、证据字段应如何组织。 |
| 从 live commerce admin、warehouse、carrier 服务重新计算异常结果。 | 会同时查询订单、库存预留和物流状态，并把多来源事实对齐到同一笔订单 / SKU / tracking。 |
| 校验 CSV 里的 issue、severity、summary totals、issue_counts 是否与重新计算结果一致。 | 会把业务规则转成稳定的异常分类和严重程度判断，并保证行级结果与汇总结果一致。 |
| 检查关键证据语义是否成立，不强绑定某个字段命名或实现方式。 | 会为每条异常保留可审计证据，例如订单状态、库存差异、承运商状态和相关 ID。 |
| 检查 solver 是否实际访问过 live 服务，并覆盖 GraphQL 分页。 | 会使用 Shopify-like GraphQL 查询订单，理解分页、variant / SKU 映射和 live 数据优先级。 |
| 检查输入数据和隐藏服务文件哈希不变。 | 明确任务应基于既有业务数据和真实本地服务完成分析，不能通过改数据或替换服务绕过对账。 |
| 检查服务在 verifier 结束时仍健康，并确认 live-only 订单没有被 stale snapshot 漏掉。 | 会区分过期快照和当前 live 服务，知道最终异常判断必须以最新订单、仓储和物流事实为准。 |


### ⚡ Skill 相关性评估

结论：强相关。

这道题里，skill 的关键价值不是泄露答案，而是把三件高成本工作标准化：

- Shopify-like GraphQL 分页与 variant 解析；
- warehouse reservation / carrier tracking 的探针路径；
- 证据更完整的异常行生成方式。

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | With Skill 已稳定全通过；Without Skill 仍未出现通过，失败原因主要是异常证据字段不够完整 |
| Agent 执行耗时 | `266.0s` | `275.5s` | With Skill 略慢约 `3.6%`，但换来稳定通过 |
| Tokens | `423,575` | `1,035,107` | With Skill 上下文更长，主要来自 helper/skill 发现与使用开销 |

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
