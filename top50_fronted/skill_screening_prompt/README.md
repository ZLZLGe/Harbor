# Skill Screening Prompt

这个目录提供一个面向“单个本地 skill 目录”的 Harbor 适配筛选 prompt。

它的用途不是直接生成 Harbor 任务，而是先回答一个更前置的问题：

- 这个 skill 是否值得保留，作为后续 Harbor 造题和小类 seed 模板归纳的输入

## 适用场景

使用前提：

1. 你已经把目标 skill 下载到本地某个目录
2. 你打算让 `Codex` 先自由探索这个目录
3. 再结合 Harbor 约束判断它是否适合造 Harbor 任务

这个 prompt 的评审单位固定为：

- 单个本地 skill 目录

不是：

- 整个 bundle
- 一个小类别下的一批 skill

## 参考依据

筛选时必须同时参考这 3 个本地来源：

1. [harbor/SKILL.md](/home/levi/.codex/skills/harbor/SKILL.md)
2. [harbor/references/task-format.md](/home/levi/.codex/skills/harbor/references/task-format.md)
3. [codex_task_builder_v3/src/prompts.ts](/home/levi/Harbor/codex_task_builder_v3/src/prompts.ts)

它们分别约束：

- Harbor task 的目录结构和运行方式
- verifier、reward、环境与任务包的基本契约
- 适合 Harbor task builder 的任务质量标准和 skill 使用方式

## 核心筛选原则

保留标准是“严格保留”。

只有当一个 skill 同时满足下面两点，才应该 `keep`：

1. 它适合被转化为可验证、可复现的 Harbor 任务
2. 在该任务里，`agent` 使用这个 skill 会明显优于不用 skill

这里有几个重要边界：

- 不要求 skill 必须自带完整现成输入资产
- 允许 `Codex` 在后续造题阶段基于 skill 的方法、规则、结构或流程合理合成输入
- 参考型、方法论型或检查清单型 skill 不默认淘汰
- 但如果它不能稳定提升 agent 表现，或者难以支撑可验证 Harbor 任务，就仍然应该 `drop`

## 使用方法

1. 打开 [single-skill-harbor-screening-prompt.md](/home/levi/Harbor/top50_fronted/skill_screening_prompt/single-skill-harbor-screening-prompt.md)
2. 把其中的 `<TARGET_SKILL_DIR>` 替换成你的本地 skill 目录
3. 让 `Codex` 先递归探索目标目录，再输出 JSON
4. 输出必须符合 [output-schema.json](/home/levi/Harbor/top50_fronted/skill_screening_prompt/output-schema.json)

## 输出说明

筛选输出固定为结构化 JSON，至少回答这些问题：

- `decision`
  这个 skill 最终应该 `keep` 还是 `drop`
- `harbor_task_adaptation_summary`
  它为什么适合或不适合被转化为 Harbor 任务
- `skill_benefit_rationale`
  为什么使用这个 skill 的 agent 会比不用 skill 更好，或者为什么不会
- `input_synthesis_feasibility`
  即使没有现成输入资产，是否仍然能基于 skill 合理造输入
- `blocking_issues`
  当前最关键的阻断点是什么
- `uncertainties`
  哪些地方仍然不确定，不能强行下判断

## 推荐用法

最稳妥的顺序是：

1. 先用这个 prompt 对单个本地 skill 做 `keep/drop`
2. 再把 `keep` 结果汇总到同一小类别
3. 最后再为该小类别总结 seed 模板线索

这样可以把“筛选 skill”和“归纳模板”拆成两个阶段，降低 prompt 目标混杂带来的误判。
