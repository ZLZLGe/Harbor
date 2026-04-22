# Code Quality 模板任务说明

这个模板面向 `code-quality` 类 Harbor 任务，但刻意不往“修 lint / 修格式 / 修单点 bug”收缩，而是对齐更真实的发布质量门禁场景。按 `2026-04-21` 浏览 `https://skillsmp.com/categories/code-quality` 时，当前页面上和本题最接近的热门方向主要集中在 `verification-loop.md`、`eval-harness.md`、`gateguard.md`、`receiving-code-review.md`、`requesting-code-review.md`、`verification-before-completion.md`、`fix.md` 和 `openclaw-release-maintainer.md` 这类“验证闭环、发布把关、审查交接”能力，而不是单纯代码美化。

本模板把这些能力压缩进一个真实可跑的结算导出发布现场：代码已经能导出日报和月报，但如果没有可靠的 spec audit、事故回放、真实 gateway 验收和正式质量资产，系统仍然会在“能跑完”和“可发布”之间失真。

## 📌 任务元数据

- 任务名：`merchant-settlement-quality-gate-hardening`
- 类别：`code-quality`
- 难度：`hard`
- 标签：`code-quality`, `quality-gate`, `functional-testing`, `integration-testing`, `spec-audit`, `settlement-reconciliation`, `python`
- 绑定 Skill：`settlement-quality-audit`
- 任务目标：在不替换真实导出链路、不绕过本地 settlement gateway 的前提下，补齐正式质量体系并恢复发布 gate

环境组成：

- `environment/workspace/`：待修复仓库，包含导出实现、发布入口、公开规格、历史事故和输出目录
- `environment/settlement-gateway/`：同容器内隐藏下游验收服务与冻结验收数据
- `environment/skills/settlement-quality-audit/`：只在 with-skill 版本存在的诊断 skill；without-skill 唯一差异就是移除此目录及对应 Dockerfile 复制逻辑

这个模板的核心不是“修一段实现”，而是要求 solver 把一次性排障沉淀成正式质量资产：

- `quality/QUALITY.md`
- `quality/test_functional.py`
- `quality/RUN_CODE_REVIEW.md`
- `quality/RUN_INTEGRATION_TESTS.md`
- `quality/RUN_SPEC_AUDIT.md`
- `AGENTS.md`

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`9/9` 通过
- Job：`code-quality-oracle-20260421-225437-g3`
- Trial：`task_oracle_e2b__mV4d3nw`

Oracle verifier 摘要：

- `test_outputs.py` 5 项全部通过
- `test_guardrails.py` 4 项全部通过
- 总耗时约 `48.6s`

Verifier 策略：

- 主测：检查正式 gate 必须保持 `export -> validate -> summarize` 顺序，生成 `gate_result.json` 与 `export_summary.md`，并让 `reference_batch` / `dirty_incident_batch` 的 daily 和 monthly 都经过真实 gateway 验收。
- 主测：检查导出结果对打乱输入顺序和替代 fixture 仍具行为稳定性，避免只对固定样例做硬编码。
- 主测：检查 gateway 使用的是冻结的隐藏服务与冻结数据，避免替换真实链路。
- 防作弊：检查正式质量资产齐全且内容实质化，而不是 TODO、占位文本或泛泛 runbook。
- 防作弊：重点要求 `RUN_SPEC_AUDIT.md` 必须沉淀 `spec summary`、`incident replay`、`gateway contract diff`，并留下可重跑审计路径，而不是只写“看了哪些文件”。
- 防作弊：禁止把任务降级成静态文件对比、假网关、关闭 dirty 场景、删除日报/月报或篡改失败退出语义。

数据来源：

- `environment/workspace/data/reference/ledger.jsonl`
- `environment/workspace/data/incidents/dirty_incident_ledger.jsonl`
- `environment/settlement-gateway/data/validation_scenarios.json`
- `environment/workspace/specs/*.md`
- `environment/workspace/incidents/*.md`

数据质量：

- 不依赖隐藏答案文件；行为标准来自公开规格、历史事故、真实导出实现和隐藏 gateway 冻结契约共同约束。
- 任务数据是冻结且可测的，但结构上保留了 posted event、refund / chargeback / manual_adjustment / reserve_release、空 batch id fallback、日报 / 月报双口径等真实复杂度。

多模态：

- 不适用。这是纯代码质量与本地服务链路任务。

## ⚡ Skill 相关性评估

结论：强相关，但价值主要体现在“稳定通过”和“把诊断结论沉淀成正式质量资产”，而不是单纯提速。

这个任务和 SkillsMP 当前 code-quality 类热门 skill 的关系更偏向：

- `verification-loop` / `eval-harness`：把一次性修复变成可重复验证的正式闭环
- `gateguard` / `openclaw-release-maintainer`：围绕发布准入、失败阻断和正式证据组织质量门禁
- `receiving-code-review` / `requesting-code-review`：要求 solver 明确风险点、证据要求和阻断条件
- `verification-before-completion`：在宣布完成前必须经真实 gateway 和正式功能测试复核

绑定的 `settlement-quality-audit` skill 并不会直接泄露修复补丁，而是把三件事标准化：

1. 从 specs 抽出 canonical evidence 和 release invariants。
2. 从 incidents 重建第一处偏差与回归证明。
3. 从 gateway contract 固化 route / field / status 语义，并把可重跑 probe 路径写回正式 runbook。

基于最近 **3 次有效对比实验**（全部是 E2B task-level 完整轨迹）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 (0%)` | `3/3 (100%)` | 当前版本已稳定形成 `with_skill pass / without_skill fail` |
| 总耗时 | `568.5s` | `641.2s` | With Skill 更慢，约多 `12.8%` |
| Agent 执行耗时 | `480.8s` | `545.7s` | With Skill 更慢，约多 `13.5%` |
| Input Tokens | `64.1k` | `70.7k` | With Skill 上下文更多，约高 `10.3%` |

这组结果说明：当前 skill 的核心价值不是节省 token 或时间，而是把 solver 拉向“更严格、更可交接”的解法，因此在本模板里体现为成功率优势而非效率优势。

最近 3 次有效实验明细：

- `with_skill`
  - `code-quality-with-skill-probe-20260421-223302-g3 / task_with_skills_e2b__UNnaQdW -> 1.0`
  - `code-quality-with-skill-probe-20260421-225614-g4 / task_with_skills_e2b__XBfGsYx -> 1.0`
  - `code-quality-with-skill-probe-20260421-232005-g5 / task_with_skills_e2b__Bw7iTyi -> 1.0`
- `without_skill`
  - `code-quality-without-skill-probe-20260421-224404-g3 / task_without_skills_e2b__YeTKHSq -> 0.0`
  - `code-quality-without-skill-probe-20260421-230934-g4 / task_without_skills_e2b__JigVw23 -> 0.0`
  - `code-quality-without-skill-probe-20260421-233104-g5 / task_without_skills_e2b__FBbMdCV -> 0.0`

Without Skill 的稳定失败模式：

- 3 次有效 trial 都没能把“可重跑审计路径”沉淀进正式 `RUN_SPEC_AUDIT.md`。
- 也就是说，without-skill 虽然通常能把代码和主链路修到接近可发布，但仍会漏掉这个模板最关键的 code-quality 要素：把诊断路径制度化、可复跑化、可交接化。
- 其中 `g4` 还额外出现了一次等价 gateway evidence wrapper 变体，但即使忽略那一项，without-skill 仍然会因为缺少 rerunnable audit evidence 而失败。

## 📁 标准目录结构说明

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

这个目录设计遵循 Harbor `skill_moban` 的模板风格：

- `instruction.md` 只讲症状、业务约束和禁止事项
- `environment/` 提供单容器真实运行环境
- `tests/` 只验证正式行为结果与防作弊 guardrails
- `solution/` 提供官方修复与 solve 入口
- `README.md` 记录模板定位、oracle、skill-effect 结果和目录说明
