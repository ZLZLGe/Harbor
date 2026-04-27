# Code-Quality Template

这是面向 `code-quality` 类 skill 的模板。它综合参考 SkillsMP testing-security / code-quality 类热门 skill 的共性能力：验证闭环、质量门禁、代码审查交接、发布阻断、eval harness、spec audit、incident replay、集成测试和可重跑证据沉淀。

## 第一部分：任务设计参考

* **Skill 价值定位**：code-quality 类 skill 的核心价值，是把“能跑”提升为“可发布、可复核、可交接”的工程质量闭环。模板任务应让 skill 在 spec evidence、incident-to-test、integration proof、review finding evidence、release gate semantics 和 rerunnable audit path 上降低漏项率，而不是只修 lint、格式或单点 bug。
* **Task目标形态**：任务应要求 Agent 在真实代码仓库和本地下游服务链路中补齐正式质量资产，并让正式 gate 通过。目标形态适合设计成质量门禁 hardening、回归测试补齐、spec audit、事故回放、contract drift 验证、发布 runbook 和 AGENTS handoff，不适合做静态文件比对、纯文档任务或只跑 happy path 的测试题。
* **Verifier设计重点**：Verifier 应运行正式 gate 和真实集成链路，验证质量资产是否实质化并能覆盖规格、事故、脏数据和下游契约。重点应覆盖输入与隐藏服务不可变、阶段顺序、真实 gateway evidence、行为引用结果、dirty data preservation、替代 fixture 泛化、`RUN_SPEC_AUDIT.md` 可重跑路径，以及反 mock / hardcode 的防作弊约束。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`merchant-settlement-quality-gate-hardening`
- 类别：`code-quality`
- 难度：`hard`
- 绑定 Skill：`settlement-quality-audit`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 在同一商家结算仓库、本地 settlement gateway、reference / dirty ledger 和公开 specs / incidents 上运行正式 gate，独立验证 `export -> validate -> summarize` 链路。它关注质量门禁是否可发布、可复跑、可交接，而不是只看代码能否生成文件。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 检查 `QUALITY.md`、功能测试、review / integration / spec audit runbook 和 `AGENTS.md` 齐全且非占位 | 正式质量资产沉淀、审查交接、发布前证据组织 |
| 校验 `gate_result.json` 的 `overall_status`、`phase_order` 和 `export_summary.md` 关键摘要 | release gate 语义、失败阻断、结果可复核 |
| 对比 reference / dirty 场景的 daily 与 monthly export 行为引用结果 | 功能回归测试、结算口径、数据质量审计 |
| 要求真实 settlement gateway 产生 4 次 accepted validation evidence | 下游契约验证、集成测试、禁止伪造 gateway |
| 覆盖 dirty adjustment、batch fallback、输入乱序和替代 fixture 泛化 | incident replay、边界场景、反硬编码能力 |
| 检查 `RUN_SPEC_AUDIT.md` 包含 spec summary、incident replay、gateway contract diff 与 probe 重跑路径 | spec audit、事故到测试、可重跑诊断路径 |
| 校验隐藏 gateway 与冻结业务数据未被篡改 | 防作弊 guardrails、真实链路保护、测试可信度 |

### ⚡ Skill 相关性评估

结论：强相关，但价值主要体现在稳定通过和正式质量资产完整性，而不是单纯提速。这个任务里，Skill 的核心价值是把规格审计、事故回放、真实 gateway 契约验证和发布质量资产标准化；without Skill 通常能接近修好主链路，但容易漏掉可重跑审计路径这类 code-quality 的关键交接证据。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均因正式质量资产缺少 rerunnable audit evidence 等问题失败；With Skill 能稳定补齐 gate 所需证据 |
| Agent 执行耗时 | `480.8s` | `545.7s` | With Skill 耗时高约 `13.5%`，但换来更完整的 spec audit、incident replay 和 gateway contract 验证 |
| Tokens | `64.1k` | `70.7k` | With Skill token 高约 `10.3%`，主要用于读取规格、事故和质量资产约束，最终显著提升通过率 |

## 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── settlement-gateway/
│   ├── workspace/
│   └── skills/
│       └── settlement-quality-audit/
├── tests/
│   ├── conftest.py
│   ├── fixtures_alt/
│   ├── test_guardrails.py
│   └── test_outputs.py
└── solution/
    ├── fixed/
    └── solve.sh
```
