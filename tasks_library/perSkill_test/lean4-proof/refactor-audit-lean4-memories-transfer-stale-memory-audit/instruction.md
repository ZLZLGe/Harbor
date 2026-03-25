你会拿到一次 Lean 4 项目重构后的审计材料。目标不是继续补证明，而是检查旧版项目记忆在这次重构之后是否还可靠，并生成一份可交给维护者继续清理的审计报告。

输入素材位于 `/app/refactor_audit_inputs/`：

- `legacy_memory_bank.json`：重构前沉淀下来的 5 条历史记录。
- `refactor_snapshot.md`：这次重构后的模块布局、证明习惯和保留规则摘要。
- `build_failures.log`：旧记录照搬到新快照后出现的构建报错摘录。
- `module_index.json`：当前快照里仍存在的模块、定理和 tactic 索引。
- `migration_guide.md`：这次重构明确给出的迁移建议与替代项。

请生成 `/app/artifacts/refactor-memory-audit.yaml`。输出必须是一个 YAML 映射，并满足以下契约：

- 顶层字段必须包含：
  - `audit_id`：字符串。
  - `audited_inputs`：字符串数组，固定列出本次审计使用的 5 个输入路径。
  - `summary`：映射。
  - `records`：数组，恰好 5 项。
  - `refresh_queue`：数组，至少 3 项。
- `audited_inputs` 必须恰好列出以下 5 个输入路径，且不多不少：
  - `/app/refactor_audit_inputs/legacy_memory_bank.json`
  - `/app/refactor_audit_inputs/refactor_snapshot.md`
  - `/app/refactor_audit_inputs/build_failures.log`
  - `/app/refactor_audit_inputs/module_index.json`
  - `/app/refactor_audit_inputs/migration_guide.md`
- `summary` 必须包含：
  - `total_records`
  - `valid_count`
  - `needs_review_count`
  - `deprecated_count`
  - `audit_focus`
- `summary.total_records` 必须等于 5。
- `summary` 中三类状态计数之和必须等于 5。

`records` 中的每一项都必须包含：

- `record_id`：字符串。
- `record_type`：字符串。
- `status`：只能是 `valid`、`needs_review`、`deprecated` 之一。
- `old_confidence`：0 到 1 之间的数值。
- `new_confidence`：0 到 1 之间的数值。
- `decision`：字符串，说明为什么这样判定。
- `suggested_update`：字符串，说明后续怎么更新这条历史记录。
- `evidence`：数组，至少 2 项；每项都必须包含：
  - `file`
  - `locator`
  - `reason`

`refresh_queue` 中的每一项都必须包含：

- `record_id`
- `priority`
- `next_step`

`refresh_queue` 约定：

- `priority` 使用数字表示，`1` 代表最高优先级。
- 队列必须按优先级从高到低排序；如果使用上述数字约定，这意味着 `priority` 数值应按从小到大排列。

证据引用要求：

- `evidence.file` 只能使用以下 5 个名字之一：
  - `legacy_memory_bank.json`
  - `refactor_snapshot.md`
  - `build_failures.log`
  - `module_index.json`
  - `migration_guide.md`
- `locator` 必须是可读的定位提示，例如行号、段落标题、键路径或错误片段。

内容要求：

- 审计范围必须覆盖 `legacy_memory_bank.json` 中全部 5 条历史记录，不能漏审。
- 最终状态分布必须是：
  - `valid` 恰好 2 条
  - `needs_review` 恰好 1 条
  - `deprecated` 恰好 2 条
- 那条围绕“闭式尾项 + 归纳”的成功套路不能直接废弃；它的核心思路仍可复用，但必须降级为 `needs_review`，并解释旧模块路径和 `simple_induction` 为什么让它需要更新。
- 那条关于“不要一上来就顶层展开递推定义”的失败经验仍然有效，必须保留为 `valid`。
- 那条关于“仓库相对路径 + line hint 或 theorem 名”的证据记录约定仍然有效，必须保留为 `valid`。
- 那条依赖 `pow_pos` 的定理记录必须标记为 `deprecated`，并在 `suggested_update` 中明确写出 `pow_pos_of_pos`。
- 那条依赖 `mod_cases n % 2` 的奇偶性套路必须标记为 `deprecated`，并说明现在应改用 `Int.ModEq` 方向。
- 对于 `needs_review` 和 `deprecated` 的条目，`new_confidence` 必须严格小于 `old_confidence`。
- `refresh_queue` 必须按优先级从高到低排序，并覆盖所有非 `valid` 的条目。

除了生成上述 YAML 文件，不要求修改别的文件。
