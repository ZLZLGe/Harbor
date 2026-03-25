你会拿到两位协作者分别导出的项目记忆、一个当前项目文件清单，以及一份简短的冲突说明。目标不是继续写证明，而是把这些材料整理成一份可交接、可审阅、可继续扩展的统一 handoff pack。

本题可直接使用当前环境中已提供的 shipped skill 来整理、合并和规范化这些记忆记录；任务预期只依赖该单个 skill，不需要其他 shipped skills。

输入素材位于 `/app/handoff_inputs/`：

- `collaborator_mira_export.json`：协作者 Mira 导出的结构化记录。
- `collaborator_noah_export.json`：协作者 Noah 导出的结构化记录。
- `project_file_inventory.json`：当前项目里允许引用的文件清单。
- `conflict_notes.md`：哪些条目应合并、保留或降级的说明。

请生成 `/app/artifacts/collab-handoff-memory-pack.json`。输出必须是一个 JSON 对象，并满足以下契约：

- 顶层字段必须包含：
  - `handoff_id`：字符串。
  - `source_exports`：字符串数组，列出你实际依赖的输入文件路径。
  - `merge_summary`：对象。
  - `merged_records`：对象。
  - `conflict_resolutions`：数组，至少 3 项。
  - `dropped_records`：数组，至少 2 项。
  - `handoff_guidance`：字符串数组，至少 3 项。
- `merge_summary` 必须包含：
  - `input_record_counts`：对象，按两个协作者导出文件名统计输入记录数。
  - `output_record_counts`：对象，至少包含 `proof_patterns`、`failed_approaches`、`project_conventions`、`theorem_dependencies` 这 4 个键。
  - `deduplicated_groups`：数组，至少 1 项；每项必须包含 `topic`、`merged_record_ids`、`kept_record_id`、`reason`。
- `merged_records` 必须包含这 4 个数组：
  - `proof_patterns`
  - `failed_approaches`
  - `project_conventions`
  - `theorem_dependencies`

每个 `merged_records` 里的条目都必须包含：

- `record_id`：字符串。
- `record_type`：字符串。
- `canonical_title`：字符串。
- `merged_from`：字符串数组，至少 1 项。
- `decision_reason`：字符串。
- `source_evidence`：数组，至少 1 项；每项都必须包含 `file` 和 `line_hint` 两个字符串字段。

不同类型的补充字段要求：

- 每个 `proof_patterns` 元素还必须包含：
  - `goal_signals`：字符串数组。
  - `recommended_steps`：字符串数组，至少 2 项。
  - `helper_lemmas`：字符串数组。
- 每个 `failed_approaches` 元素还必须包含：
  - `attempted_step`
  - `failure_signal`
  - `better_direction`
- 每个 `project_conventions` 元素还必须包含：
  - `rule`
  - `reason`
- 每个 `theorem_dependencies` 元素还必须包含：
  - `theorem`
  - `why_it_matters`
  - `preferred_source`

`conflict_resolutions` 的每一项都必须包含：

- `topic`
- `winner_record_id`
- `loser_record_ids`
- `resolution_reason`

`dropped_records` 的每一项都必须包含：

- `record_id`
- `drop_reason`
- `replaced_by`

内容要求：

- 你必须把语义上重复的成功套路合并成一个 canonical proof pattern，而不是把两个近似条目原样并列保留。
- 当两个候选条目冲突时，应优先保留证据更强、可复查性更高的记录，并把原因写进 `decision_reason` 或 `resolution_reason`。
- 两条失败经验都要保留，因为它们描述的是不同的死路。
- 证据引用规范最终只能保留一条 canonical convention，而且这条 convention 必须明确要求“仓库相对路径 + 本地 line hint 或 theorem 名”。
- 关于正性尾项的依赖记录最终只能保留一条 canonical dependency，并且应优先选择“显式定理依赖”，而不是只写自动化 tactic 名字的版本。
- 每个 `source_evidence.file` 和每个 `preferred_source` 都必须出现在 `project_file_inventory.json` 的已跟踪文件列表中。
- `handoff_guidance` 应面向下一位接手的人，说明这个 handoff pack 接下来该怎么用，而不是复述输入内容。

除了生成上述 JSON 文件，不要求修改别的文件。
