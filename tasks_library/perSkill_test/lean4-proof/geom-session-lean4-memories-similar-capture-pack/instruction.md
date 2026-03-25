你会拿到一份 Lean 4 证明会话的整理素材，目标是把其中可复用的信息沉淀成一个结构化 JSON 文件。这是一个从证明会话中提炼可复用经验的整理任务。

输入素材位于 `/app/session_assets/`：

- `geom_bound_session.lean`：一个已经完成的几何级数上界证明，会展示成功思路。
- `failed_attempts.md`：同一会话里若干失败尝试的摘录。
- `project_conventions.md`：这个项目记录证明经验时使用的简短约定。

请生成 `/app/artifacts/geom-session-memory-pack.json`。输出必须是一个 JSON 对象，并满足以下契约：

- 顶层字段必须包含：
  - `session_id`：字符串。
  - `source_files`：字符串数组，列出你实际引用的输入文件路径。
  - `proof_patterns`：数组，至少 1 项。
  - `failed_approaches`：数组，至少 1 项。
  - `project_conventions`：数组，至少 1 项。
  - `reuse_advice`：字符串数组，至少 2 项。
- 每个 `proof_patterns` 元素必须包含：
  - `name`：字符串。
  - `goal_shape`：字符串。
  - `strategy`：字符串。
  - `supporting_details`：对象，且必须包含 `tactics`（字符串数组）与 `helper_lemmas`（字符串数组，可为空）。
  - `source_evidence`：数组，至少 1 项；每项都必须包含 `file` 和 `quote_or_line_hint` 两个字符串字段。
- 每个 `failed_approaches` 元素必须包含：
  - `name`、`attempted_step`、`failure_signal`、`why_it_failed`、`better_direction`。
  - `source_evidence`：格式与上面一致。
- 每个 `project_conventions` 元素必须包含：
  - `name`、`rule`、`reason`。
  - `source_evidence`：格式与上面一致。

内容要求：

- 所有条目都必须明确来自给定素材，不要编造未出现的定理、错误或项目规则。
- `proof_patterns` 里至少有一条要清楚总结出这个会话中的成功证明套路，能够帮助后续处理同类“递推定义的数列上界”问题。
- `failed_approaches` 里至少有一条要总结失败尝试，并写明更好的替代方向。
- `project_conventions` 里至少有一条要反映项目如何记录证据或如何描述可复用经验。
- `reuse_advice` 需要写成面向下一次同类任务的简短建议。
- 各数组中的条目顺序不重要，但至少要有某个条目满足对应内容要求。

除了生成上述 JSON，不要求修改别的文件。
