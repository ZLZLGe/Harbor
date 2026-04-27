# CI Flake Triage Template

这是面向 CI/CD 类 skill 的模板。它按 SkillsMP CI/CD 分类页的 stars 排序优先参考高热度 skill，抽象它们在 CI 日志诊断、测试优化、流水线验证、部署检查和可审计输出上的共性能力。

## 第一部分：任务设计参考

* **Skill 价值定位**：高星 CI/CD skill 的共同价值不是“替 agent 写答案”，而是把 CI 日志、平台状态、测试命令、部署健康信号组织成可复现的诊断流程。它们强调先取证、再复现、再分类，避免只凭错误文本猜测。
* **Task 目标形态**：模板任务应提供真实风格的 CI 产物、仓库脚本和运行链路，让 solver 产出结构化报告、复现记录和标准 diff。任务重点应靠流程判断、行为验证和证据完整性拉开 skill 差距，而不是靠隐藏答案或单纯 app 修复。
* **Verifier 设计重点**：Verifier 应同时检查最终产物和命令轨迹，确认 solver 是否运行了目标 suite、是否精确复现失败、是否比较了环境差异、是否保留业务断言。防作弊测试要拦住跳过复现、全量粗暴测试、修改输入日志、禁用测试或用长 timeout 掩盖问题的解法。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`playwright-prod-bundle-flake-triage`
- 类别：CI/CD
- 难度：`hard`
- 绑定 Skill：`triage-ci-flake`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法先抽取 CI 失败信息，再用 `pnpm dev checkout` 和 `pnpm dev:prod checkout` 对同一个 Playwright 标题做 targeted reproduction，最后输出 JSON 报告、复现 notes 和统一 diff。
- Verifier 策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 检查 `flake_report.json`、`reproduction_notes.md` 和 `recommended_fix.diff` 的内容 | 从 CI 日志抽取 suite、test file、test title、error，并写出可审计结论 |
| 检查 `.trace/commands.jsonl` 中 dev/prod targeted reproduction 顺序 | 先运行复现流程，再分类问题 |
| 禁止 full suite、skip/fixme、超长 timeout 和修改输入 CI 文件 | 保留真实链路与业务断言，不用规避方式通过 |
| 验证 dev pass、prod fail 后分类为 `prod_bundle_regression` | 区分本地 dev 与生产 bundle 环境差异 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是强制 agent 在分析前执行 CI flake 复现路径，包括清理端口、启动目标 suite、运行精确 Playwright 标题、再切到 production-bundled 链路。没有 skill 的 agent 倾向于从日志和 `package.json` 推断，或走 `npm run` 等错误入口，导致 verifier 的行为轨迹失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | Without Skill 三次都未完整执行 `lsof`/`pnpm dev`/`pnpm dev:prod` 复现链路；With Skill 三次都通过全部 verifier。 |
| Agent 执行耗时 | `197.5s` | `213.6s` | With Skill 完整跑完 dev/prod 复现和产物校验；Without Skill 较快结束但留下行为轨迹失败。 |
| Tokens | `341K` | `448K` | With Skill 使用更多上下文完成证据链和报告；Without Skill token 较少但没有满足复现流程。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── ci-logs/
│   ├── repo/
│   └── skills/
├── tests/
└── solution/
```