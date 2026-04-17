# Astronomy-Physics 模板任务设计说明

本模板面向 `astronomy-physics` 类技能任务，目标不是做“修一段坏代码”的调试题，而是构造一条真实、可运行、可审计的科学分析交付链路。当前示例任务聚焦于 TESS 风格多目标光变 vetting：solver 需要读取冻结数据、调用本地 manifest / audit 服务、完成清洗与周期分析，并产出最终 bundle。

## 第一部分：模板范式

围绕 astronomy-physics 类热门 skill 设计任务时，建议遵循以下原则：

1. 任务要是结果导向的科学分析题，不要把题面锚死在“修某个函数/模块”。更好的形态是：给定数据、约束和真实链路，要求 solver 生成正式交付物。
2. Skill 的价值应来自标准化科学 workflow，而不是塞答案。典型价值包括：质量控制、异常窗口处理、周期搜索职责分离、odd/even 诊断、secondary eclipse 检查、最终审计提交。
3. without-skill 仍应理论可解，但需要自己重建整条诊断与收敛路径；with-skill 则能显著降低定位和收口成本。
4. 环境里要保留真实风格上下游依赖。对于 astronomy-physics 类任务，推荐使用本地 catalog/manifest 服务、冻结观测快照、审计 API 或隐藏校验逻辑，而不是只给一个静态 CSV。
5. Verifier 只验行为结果，不绑定唯一实现。只要 solver 使用真实链路，产物满足科学与业务约束，就应允许不同分析脚本通过。
6. Guardrails 必须能拦住伪修复。应显式防止硬编码 bundle、跳过审计、伪造 receipt、篡改隐藏服务、修改原始数据、绕开 manifest 等行为。
7. with-skill 与 without-skill 的唯一差异只能来自 `environment/skills/` 及其复制逻辑；题面、测试、数据、依赖和隐藏服务都必须一致。

这类任务对 skill 的验收标准，建议至少覆盖：

- 是否帮助 solver 更快发现正确的数据清洗和周期搜索职责分工。
- 是否帮助 solver 更稳定地走通 manifest -> analysis -> audit 的真实链路。
- 是否在最近至少 3 次有效对照里形成稳定差异，而不是依赖人为压 timeout。

## 第二部分：示例任务

当前示例任务名为 `tess-multi-target-vetting-bundle`，题型为 analysis-output。

### 📌 任务元数据

- 任务名称：`tess-multi-target-vetting-bundle`
- 类别：`astronomy-physics`
- 难度：`hard`
- 标签：`astronomy`, `exoplanet`, `timeseries`, `light-curve-analysis`, `astropy`, `box-least-squares`, `lomb-scargle`, `vetting`
- 绑定 Skill：`exoplanet-workflows`

任务说明：

- Solver 需要读取本地 `catalog` 中的全部目标。
- 对每个目标合并 3 段 light curve，结合 `quality_flag` 和 `manifest quarantine_windows_mjd` 做清洗。
- 区分 rotation alias、planet-like transit 和 eclipsing binary 信号。
- 生成 `/app/output/catalog_vetting.json` 与 `/app/output/catalog_audit_receipt.json`。
- 最终 bundle 必须通过真实 `POST /audit`，且 verifier 会重放链路、校验 trace 与 canonical hash。

任务中的 4 个目标覆盖了不同诊断场景：

- `TIC-220039452`：强 rotational modulation 覆盖下的 planet candidate。
- `TIC-146712781`：naive BLS 容易命中 half-period 的 EB trap。
- `TIC-381920550`：需要 secondary eclipse 诊断的 false positive。
- `TIC-440119211`：只有正确应用 quarantine window 才能去掉短周期假解的 planet candidate。

### 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 最新 oracle 样本：`astronomy-template-oracle-e2b-20260417a`

Verifier 策略：

- 主测：检查 `/app/output/catalog_vetting.json` 与 `/app/output/catalog_audit_receipt.json` 是否存在、结构正确，并覆盖 catalog 的全部目标。
- 主测：检查每个 entry 的关键科学字段、自洽计数和 `verdict_reason` 质量。
- 主测：重放真实 `POST /audit`，要求最终 bundle 仍然能被 live audit 接受。
- 主测：要求 solver 实际调用 live `/catalog`、`/manifest/<target_id>` 和 `/audit`，并通过 trace 验证真实链路。
- 防作弊：要求 receipt 中的 `request_sha256` 与 canonical final payload 一致，防止伪造或先审计后改报告。
- 防作弊：保护隐藏 observatory API 与原始数据不被修改，阻止静态 bundle、假 receipt 和跳过 manifest 的伪修复。

数据质量：

- 数据是冻结的 TESS 风格多扇区 2-minute cadence photometry。
- 每个目标都包含真实风格的质量标记、quarantine 窗口和不同类型的周期诊断陷阱。
- 数据保持确定性与可测性，但足以逼出真实的清洗、flatten、LS/BLS、odd/even 与 secondary-eclipse 工作流。

多模态：

- 不适用（纯数值分析与结构化交付物任务）。

### ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值不是“直接给答案”，而是把多目标 vetting workflow 标准化：

- 先走 live catalog / manifest。
- 再按 quality 与 quarantine 分层清洗。
- 用 Lomb-Scargle 识别 rotation alias。
- 用 BoxLeastSquares 做 transit candidate 与 doubled-period 诊断。
- 最后把真实 final bundle 通过 live audit 提交，并写出 verifier 所需的 compact receipt。

没有 Skill 时，solver 虽然仍可能把主要科学部分做对，但更容易在最后的交付收口上出错，尤其是：

- 没有保证 receipt 的 `request_sha256` 来自 canonical final payload。
- 先提交一版 bundle，再改本地报告，导致 audit trace 与最终交付物脱节。
- 自己重写提交流程时忽略 verifier 对 compact receipt 的行为约束。

基于当前最新的有效对照样本：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/1 (0%)` | `1/1 (100%)` | 最新有效对照中，with-skill 完整通过，without-skill 留下 1 个 verifier 失败 |
| 关键失败点 | `request_sha256` 与 final bundle hash 不一致 | 无 | without-skill 主要失败在最后的真实交付收口，而不是 setup 或 timeout |

当前已确认的一组干净样本：

- with-skill：`astronomy-template-with-skills-e2b-20260417c`，trial `task_with_skills_e2b__aRQnswB`，`reward = 1.0`
- without-skill：`astronomy-template-without-skills-e2b-20260417c`，trial `task_without_skills_e2b__EL5NccT`，`reward = 0.0`

without-skill 当前失败原因：

- live audit 已接受其 bundle。
- 但 solver 在 receipt 中写入的 `request_sha256` 与最终 `/app/output/catalog_vetting.json` 的 canonical hash 不一致。
- verifier 因此在 `test_b_solver_used_live_catalog_manifest_and_audit_chain` 失败，说明它没有把“最终交付物”和“真实审计请求”保持一致。

说明：

- 上表会继续补到最近至少 3 次有效对照样本后再作为最终统计口径。
- 当前这组结果已经证明：差异来自真实 verifier 行为约束，不是 setup 失败，也不是 agent 没开始做题。

### 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
└── solution/
```
