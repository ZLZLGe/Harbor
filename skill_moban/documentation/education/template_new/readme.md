# Education Template: New Analyst Lesson Notebook Repair

本模板面向 `education` 类 Harbor 任务，设计目标对齐 SkillsMP 里更热门、也更适合模板化复用的技能方向：`jupyter-notebook`、`technical-writer`、lesson planning、tutorial asset generation。任务不是修 app，也不是开放式写作，而是把冻结的课程素材、真实风格学习数据和草稿教学资产收敛成一套可运行、可验证、可复核的正式课程交付物。

## 📌 任务元数据

- 任务 ID：`education__new-analyst-lesson-notebook-repair`
- 类别：`education`
- 难度：`hard`
- 绑定 Skill：`lesson-notebook-diagnostics`
- 主要交付物：
  - `/app/output/student_lesson.ipynb`
  - `/app/output/instructor_guide.md`
  - `/app/output/lesson_manifest.json`
  - `/app/output/source_map.json`
  - `/app/output/final_package.json`

该任务要求 solver：

- 基于真实可运行的数据分析素材，整理一份面向初学者的 lesson notebook。
- 同时补齐与 notebook 对齐的 instructor guide。
- 用 `lesson_manifest.json` 与 `source_map.json` 把章节、来源和关键结论收口成可复核的清单。
- 最后通过 `build_lesson_package.py` 产出正式 `final_package.json`。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 作业：`education_v3_oracle_20260422_190201`
- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`12/12` 通过

Verifier 策略：

- 主测：检查 notebook、guide、manifest、source map 和 final package 是否存在、可解析，并满足固定章节顺序与输出结构。
- 主测：执行 notebook，确认其真实读取 `learner_events.csv`、`quiz_attempts.csv`、`quiz_items.csv`、`metric_definitions.yaml`，并产生非空表格或图表输出。
- 主测：检查 bundle 是否解释关键指标、覆盖题目误区、并让 guide 与 notebook 在 `Retry behavior` 等教学结论上保持一致。
- 主测：检查 `Practice` 章节是否是 source-grounded 的练习块，而不是泛泛提问；要求其同时回扣事件漏斗、指标口径和题目误区三条教学主线。
- 主测：运行 `build_lesson_package.py`，要求正式打包链路成功生成 `final_package.json`。
- 防作弊：保护冻结输入；拦截空壳 notebook、纯 markdown 总结、伪造数据分析、以及手写 `final_package.json` 的伪打包。

数据来源：

- `lesson_brief.md`
- `learner_events.csv`
- `quiz_attempts.csv`
- `quiz_items.csv`
- `metric_definitions.yaml`
- `reference_docs/glossary.md`
- `reference_docs/facilitation_notes.md`

多模态：

- 不适用（Jupyter notebook + 结构化 manifest 任务）。

## ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值是把 lesson-bundle 修复流程标准化：先走 repair entrypoint，再对章节顺序、来源引用、practice block 和 metric-definition 一致性做脚本化诊断。没有 skill 时，solver 理论上仍可直接重写 notebook 和 guide；但在这个任务上，最容易漏掉的不是“会不会画表”，而是教学细节是否同时满足可追溯、可讲授、可练习三件事。最近三次有效对照里，without-skill 的典型失败都卡在讲义未正确覆盖顶层 misconception `Retry behavior`。

基于最近 **3 次有效对照实验**（均为真正跑到 task-level、存在完整 agent 轨迹；已排除模板构建被取消的无效 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | With Skill 已稳定通过；Without Skill 在最近 3 次有效试验中均未通过 |
| 平均总耗时 | `514.5s` | `341.7s` | With Skill 更快，平均总耗时降低约 `34%` |
| 平均 Agent 执行耗时 | `424.7s` | `247.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `42%` |
| 平均 Input Tokens | `405,621` | `493,757` | With Skill 读取诊断脚本与修复入口带来额外上下文开销，但换来了显著更高的通过率和更短的收敛时间 |

有效对照作业：

- `education_v3_pairG_with_20260422_183327` / `education_v3_pairG_without_20260422_183327`
- `education_v3_pairH_with_20260422_184328` / `education_v3_pairH_without_20260422_184329`
- `education_v3_pairI_with_20260422_185157` / `education_v3_pairI_without_20260422_185157`

超时设定说明：

- 最近 3 次有效 `with_skill` 平均总时长约 `341.7s`
- 按规则取 `2x with_skill` 并向上取整到最近的 `100s`，得到 `700s`
- 因而本任务 `timeout_sec` 设为 `700`

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
