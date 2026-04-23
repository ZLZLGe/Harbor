# Astronomy-Physics 模板任务设计说明

本模板面向 `astronomy-physics` 类技能任务。当前示例任务聚焦于 TESS 风格多目标光变 vetting：solver 需要读取冻结数据、调用本地 manifest / audit 服务、完成清洗与周期分析，并产出最终 bundle。

## 第一部分：任务设计参考
* **Skill 价值定位**：技能收益必须体现在天文/物理判断链路中，例如单位换算、坐标或时间系统处理、观测量解释、误差边界评估、物理模型选择等；严禁把任务难点主要设计成体力编码、文件搬运或通用数据清洗。
* **任务目标形态**：任务应要求 Agent 产出可验证的科学结果，例如目标分类、候选筛选、参数估计、异常识别、模型对比或结论报告；不应只要求复述资料、整理文本或生成缺乏科学判定的普通摘要。
* **验证设计重点**：Verifier 应关注物理语义和结果一致性，例如数值容差、单位正确性、边界条件、证据引用和推理链完整性；对于自由文本输出，应避免固定关键词、固定短语或唯一措辞匹配，除非题面已明确把这些字面形式写成验收要求。

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
- 生成 `/app/output/catalog_vetting.json` 与 `/app/output/catalog_audit_receipt.json`两份文件，交由verifer验证正确性。

任务中的 4 个目标覆盖了不同诊断场景：

- `TIC-220039452`：强 rotational modulation 覆盖下的 planet candidate。
- `TIC-146712781`：naive BLS 容易命中 half-period 的 EB trap。
- `TIC-381920550`：需要 secondary eclipse 诊断的 false positive。
- `TIC-440119211`：只有正确应用 quarantine window 才能去掉短周期假解的 planet candidate。

### 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）

Verifier 策略：

- 主测：检查 `/app/output/catalog_vetting.json` 与 `/app/output/catalog_audit_receipt.json` 是否存在、结构正确、覆盖全部目标，并验证关键科学字段、自洽计数、`verdict_reason` 质量、live `/catalog` / `/manifest/<target_id>` / `/audit` 调用链与最终 audit 接受结果。
- 防作弊：要求 receipt 中的 `request_sha256` 与 canonical final payload 一致，并保护隐藏 observatory API 与原始数据不被修改，阻止静态 bundle、假 receipt、跳过 manifest、先审计后改报告等伪修复。

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
