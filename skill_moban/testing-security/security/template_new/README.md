# Security Template

这是面向 `security` 类 skill 的模板。它综合参考 SkillsMP 安全类热门 skill 的共性能力：认证与授权检查、租户隔离确认、限流与配额观察、错误信息暴露判断，以及把检查结果沉淀为可交付的证据包与审计报告。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类热门 skill 的价值，主要体现在把 API 安全检查串成一条可执行链路，让 Agent 能从接口发现、身份切换、对象级授权、输入边界到错误语义一路收口。模板题面应把重心放在交付物、业务范围和约束条件，让具体排查顺序由 skill 与 solver 自行展开。
* **Task 目标形态**：适合设计成带有多身份、多租户、多接口面的本地服务审计任务。目标应要求 solver 直接操作运行中的系统、提取证据、写出结构化结论，并保证每次执行都能稳定复现。
* **Verifier 设计重点**：Verifier 应优先检查 solver 是否真的走过了 live API 审计链路，是否覆盖了关键身份与关键接口，是否把结论落实到证据文件。防作弊点要覆盖伪造报告、只做静态阅读、只对样例特判以及改动输入或环境文件。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`security__orderhub-api-security-review`
- 类别：`security`
- 难度：`hard`
- 绑定 Skill：`api-security-testing`
- 输入数据参考来源：
  - `environment/data/contracts/orderhub-public-openapi.yaml`：任务内 API 合同文件；设计形态参考 OpenAPI 3.0.3  
    https://spec.openapis.org/oas/v3.0.3
  - `environment/data/engagement/rules_of_engagement.md`、`environment/data/engagement/target_profile.json`：任务内审计边界、请求预算与身份约束；组织方式参考通用渗透测试 pre-engagement 实践  
    https://csrc.nist.gov/pubs/sp/800/115/final  
    https://csrc.nist.gov/glossary/term/rules_of_engagement  
    https://pentest-standard.readthedocs.io/en/latest/preengagement_interactions.html
  - `environment/data/seed/customers.json`、`orders.json`、`order_details.csv`、`products.json`、`employees.json`、`shippers.json`：任务内订单域快照；数据形态参考 Northwind sample database  
    https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/northwind-pubs
  - `environment/data/tenancy/account_map.json`：任务内租户与账户映射；为本模板本地输入

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 通过 `solution/solve.sh` 直接审计本地运行中的 OrderHub API，生成结构化 findings、复现文档和证据目录，再运行 verifier 验证全部测试点。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 接口发现与身份覆盖 | 检查 solver 是否读取公开合同并覆盖全部给定身份 | API discovery、authentication |
| 对象级授权确认 | 检查是否完成跨租户订单读取并记录证据 | authorization、multi-tenant isolation |
| 导出与限流确认 | 检查是否执行跨租户导出和连续请求序列 | rate limiting、sensitive export review |
| 错误暴露确认 | 检查是否触发错误路径并保留回溯与 SQL 片段证据 | error handling、input validation follow-through |
| 输出交付合同 | 检查 findings、reproduction 和 evidence 目录结构与内容 | report generation、evidence discipline |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| Live API 轨迹 | 通过访问日志确认 solver 走过了要求的审计动作 |
| 输入与服务完整性 | 校验 `/root/data` 和隐藏服务文件 hash 未变化 |
| Skill 完整性 | 校验已安装的 skill 文件未被改动 |
| 服务健康 | 验证审计结束后目标服务仍可正常响应 |

### ⚡ Skill 相关性评估

结论：待实验补充。这个任务与 `api-security-testing` 的相关性很强，因为核心工作集中在接口发现、身份切换、对象级授权、限流观察和错误处理确认。对照实验完成后，会把最近至少 3 次有效 with_skill / without_skill 结果补入下表。

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `待补` | `待补` | 待实验补充 |
| Agent 执行耗时 | `待补` | `待补` | 待实验补充 |
| Tokens | `待补` | `待补` | 待实验补充 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
