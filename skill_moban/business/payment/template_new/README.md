# Payment Template

这是面向 `payment` 类 skill 的模板。它综合参考 SkillsMP payment 类热门 skill 的共性能力：票据识别、供应商归一化、付款批次审查、重复单据判定、当前状态核验、归档路径整理，以及把多来源付款事实收口成可审计交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：payment 类热门 skill 的核心价值，是把分散在票据目录、供应商主数据、付款状态 service 和批次规则里的事实，组织成一条稳定的应付账款处理链路。模板任务应让 skill 在目录遍历、字段提取、供应商统一、重复判定、付款状态核验和交付物收口这些环节降低试错成本。
* **Task 目标形态**：任务应落在应付账款团队的单据整理、付款批次审查或结算复核场景里，要求 Agent 结合票据样本、主数据、快照、规则文件和容器内 service，产出结构化台账、批次结果和操作说明。题面应重点交代正式交付物、业务约束和禁止事项，把检索顺序、提取细节和判定步骤更多留给 skill 和 solver 自主识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了完整业务链路和关键动作，并检查单据台账、批次纳入结果、重复判定、service 访问和归档副本是否一致。重点应覆盖嵌套目录遍历、容器内 AP review service 优先级、快照规避、分页与明细抓取、路径命名规则、输入不可改和输出副本完整性。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`payment__invoice_batch_review`
- 类别：`payment`
- 难度：`hard`
- 绑定 Skill：`invoice-organizer`
- 输入数据参考来源：
  - `environment/data/inbox/cloud/aws/statement-2014-08.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.pdf
  - `environment/data/inbox/facilities/azure/q1-office-renewal.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AzureInterior.pdf
  - `environment/data/inbox/retail/flipkart/card-accessory-bill.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/FlipkartInvoice.pdf
  - `environment/data/inbox/legal/netpresse-publication-invoice.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/NetpresseInvoice.pdf
  - `environment/data/inbox/infra/qualityhosting/mail-hosting-may.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/QualityHosting.pdf
  - `environment/data/inbox/telco/free/fiber-july.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/free_fiber.pdf
  - `environment/data/inbox/office/coolblue/hardware-order.pdf`：任务内票据样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/coolblue1.pdf
  - `environment/data/inbox/fuel/orlen/mobile-pay.txt`：任务内票据文本样本；直接来源于  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/Orlen.txt
  - `environment/data/inbox/misc/reimports/aws-statement-duplicate.pdf`：任务内重复导入样本；内容设计形态参考  
    https://raw.githubusercontent.com/invoice-x/invoice2data/master/tests/compare/AmazonWebServices.pdf
  - `environment/data/vendor_master.csv`：任务内供应商主数据；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/settlement_snapshot.csv`：任务内较早导出的付款状态快照；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/batch_context.json`：任务内批次上下文与 service 入口；为模板整理后的本地业务输入，无单独公开数据链接
  - `environment/data/filing_policy.yaml`：任务内命名、归档和重复判定规则；为模板整理后的本地业务输入，无单独公开数据链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：oracle 使用题面给定的票据样本、供应商主数据、批次上下文、规则文件和容器内 AP review service，独立重算单据台账、批次纳入结果、币种汇总、service 检查状态和批次说明内容。它证明任务可运行、可验证，并且不依赖隐藏答案文件。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 `invoice_register.csv`、`payment_batch.json` 和 `batch_review.md` 是否存在、可解析，并包含必需字段、列名和顶层键 | 先理解正式交付合同，再组织结构化结果 |
| 目录遍历与台账重算 | 递归重算全部输入单据的文件级结果，并核对供应商归一化、单据编号、日期、金额、币种和费用类别 | 目录扫描、字段提取、供应商统一和台账整理 |
| 当前状态与纳入判定 | 结合 AP review service、批次范围和规则文件，重算 `payment_status`、`eligible_for_batch`、`exclusion_reason` 和 `notes` | 当前状态核验、批次判定和人工复核收口 |
| 重复组与归档路径 | 校验重复组保留项、重复项、标准路径和标准文件名是否满足 policy | 重复判定、命名规则和归档整理 |
| 批次汇总一致性 | 校验 `payable_documents`、`excluded_documents`、`currency_totals`、`service_checks` 与台账结果一致 | 批次汇总、结果闭环和可审计输出 |
| 批次说明语义 | 检查批次说明是否覆盖单据总数、可付款数量、不可纳入项、人工复核项、重复项和币种汇总 | 面向运营同事的交付说明整理 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| service 访问与分页 | 访问日志必须证明 solver 读取了 manifest，遍历了全部 document page，并抓取了每份单据的 review 明细 |
| 快照规避 | 仅依赖 `settlement_snapshot.csv` 不能通过；仅来自 service 的记录也必须出现在输出中 |
| 数据与环境完整性 | `/root/data/`、隐藏 service 文件和 skill 目录内容不得变化；service 在 verifier 结束时仍健康 |
| 输出副本完整性 | 每条台账记录都必须对应整理后文件副本，且副本内容与源文件哈希一致 |
| 路径与扩展名 | 整理后文件路径必须满足 `filing_policy.yaml`，并保留原始扩展名 |

### ⚡ Skill 相关性评估

结论：相关性较强。这个任务里，Skill 的核心价值是把票据目录扫描、字段提取、供应商归一化、重复组处理、状态核验和批次收口串成一条工作流，从而降低在多语言票据、分页 review service 和整理副本联动上的试错成本。without Skill 仍然可解，但更容易停在发票号抽取、批次纳入和归档路径联动错误这类行动级失败上。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 近 3 次有效对照里，without Skill 为 `0/3`；with Skill 为 `1/3`。without Skill 主要败在多语言发票号抽取，以及随后的批次清单与整理副本联动错误。 |
| Agent 执行耗时 | `527.8s` | `444.7s` | With Skill 的平均 Agent 耗时降低约 `15.8%`。 |
| Tokens | `889855` | `777221` | Without Skill 的平均 token 开销约为 With Skill 的 `1.14x`。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── README.md               # 模板说明、任务设计参考、示例任务和实验结果
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义；在同一容器内启动 AP review service 与隐藏下游服务
│   ├── data/               # 任务输入数据、规则文件和批次上下文
│   ├── hidden-service-src/ # 本地 AP review service 实现与数据
│   └── skills/             # 任务绑定的 payment skill 定义与辅助脚本
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考修复代码及 solve.sh
```
