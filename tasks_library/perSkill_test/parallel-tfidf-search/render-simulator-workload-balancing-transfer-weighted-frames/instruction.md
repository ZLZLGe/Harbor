# Transfer: Weighted Frame Render Scheduling

在 `/root/workspace/` 中，已经提供了一个本地渲染农场调度仿真器和输入资产：

- `/root/workspace/render_baseline.py`
- `/root/workspace/scene_catalog.json`
- `/root/workspace/render_frames.csv`

这些帧按镜头顺序排列，但不同场景的渲染成本差异很大；直接按连续区间分给 worker，会让尾部 chunk 明显拖慢总完成时间。你需要在 `/root/workspace/render_scheduler.py` 中实现一个更合理的帧调度器。

你必须实现这个函数：

1. `schedule_weighted_frames(frame_path="/root/workspace/render_frames.csv", scene_path="/root/workspace/scene_catalog.json", output_path="/root/workspace/render_schedule_summary.json", num_workers=4)`

函数要求：

- 读取场景目录和帧清单，为每一帧分配一个 worker。
- 把调度汇总写入 `output_path` 指向的 JSON 文件，并返回同一个汇总对象。
- 每一帧必须被处理且只能被处理一次。
- `worker_summaries` 中的 `frames` 必须表示该 worker 的渲染顺序。

输出 JSON 至少必须包含这些顶层字段：

- `num_workers`
- `total_frames`
- `total_predicted_cost`
- `total_actual_duration`
- `makespan`
- `worker_summaries`
- `scene_totals`

其中 `worker_summaries` 必须是长度等于 `num_workers` 的列表；每个元素都至少包含：

- `worker_id`
- `frame_count`
- `scene_count`
- `predicted_load`
- `actual_duration`
- `frames`

其中 `scene_totals` 必须是 `scene_id -> summary` 的映射；每个场景 summary 都至少包含：

- `scene_name`
- `frame_count`
- `predicted_cost`
- `actual_duration`

判定要求：

- 输出 JSON 文件内容必须与函数返回值一致。
- 所有帧都必须被覆盖，且不能重复。
- `total_frames`、`total_predicted_cost`、`total_actual_duration`、`makespan`、每个 worker 的聚合值，以及每个场景的聚合值都必须和实际调度结果一致。
- 不要修改提供的基线文件或输入资产。

调度质量要求：

- 使用给定资产、`num_workers=4` 时，你的 `makespan` 必须严格小于 `render_baseline.py` 中 `run_contiguous_interval_baseline(...)` 的结果。
- 同一条件下，你的 `makespan` 还必须不高于连续区间基线的 `0.60x`。

说明：

- 可以复用基线里的数据加载和汇总辅助函数。
- 只要输出契约满足要求，内部调度策略不限。
