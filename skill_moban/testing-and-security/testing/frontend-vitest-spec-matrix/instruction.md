你是一名前端测试工程师。请读取 `/app/workspace/frontend_targets.csv`，根据每个前端目标生成一份 Vitest + React Testing Library 测试规划矩阵，并写入 `/app/workspace/output/frontend_test_matrix.csv`。

输入 CSV 至少包含以下字段：

- `target_id`
- `target_type`
- `has_async`
- `has_query_state`
- `has_http_mock`
- `has_error_state`
- `complexity`

输出 CSV 必须严格使用以下列顺序：

`target_id,test_style,required_scenarios,mock_strategy,rtl_tools,coverage_goal,execution_order`

要求：

- 仅输出上述 7 列，不能添加其他列。
- 结果按 `target_id` 升序排序。
- 不要输出空字符串、`null`、`None`、`N/A`、`undefined` 等空值占位文本。
- 内容要体现该技能目录强调的方法：
  - 使用 Vitest + RTL。
  - 以黑盒测试为主。
  - 按复杂度渐进执行。
  - 包含必测场景。
  - 若存在 query-state，则覆盖 `nuqs`/URL query state。
  - 使用语义化选择器。
  - 若存在异步行为，则体现异步等待与稳定化。
- `execution_order` 需要反映“先简单后复杂”的推荐执行顺序，但最终输出行仍然必须按 `target_id` 排序。

请只依赖本地文件，离线、确定性地完成任务。
