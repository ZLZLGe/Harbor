## 任务说明

请读取 `/app/workspace/data/picking_events.csv` 与 `/app/workspace/data/shifts.csv`，并覆盖 `/app/workspace/` 根目录中已经放好的目标工作簿文件；目标文件主文件名为 `warehouse_kpi_dashboard`。

输出工作簿必须且只能包含以下 4 个工作表，名称与顺序都要一致：

1. `raw_events`
2. `shift_summary`
3. `exceptions`
4. `dashboard`

具体要求如下：

### 1. `raw_events`

- 第一行必须是表头
- 列严格为：
  - `event_id`
  - `shift_id`
  - `picker_id`
  - `item_sku`
  - `units_picked`
  - `active_seconds`
  - `scan_started_at`
  - `scan_finished_at`
  - `overdue_flag`
  - `exception_flag`
  - `exception_reason`
- 数据行按 `picking_events.csv` 原始顺序写入，不要改写字段内容

### 2. `shift_summary`

- 第一行必须是表头
- 列严格为：
  - `shift_id`
  - `shift_date`
  - `zone`
  - `picker_count`
  - `target_secs_per_unit`
  - `event_count`
  - `units_picked`
  - `total_active_seconds`
  - `avg_secs_per_unit`
  - `overdue_rate`
  - `exception_count`
  - `exception_rate`
  - `efficiency_gap`
- 前 5 列按 `shifts.csv` 原始顺序逐行写入
- 每个班次 1 行，行顺序与 `shifts.csv` 保持一致
- 从 `event_count` 到 `efficiency_gap` 这 8 列必须由工作表公式计算，不能把计算结果直接写成常量
- 如果某个班次没有对应事件，则 `event_count`、`units_picked`、`total_active_seconds`、`avg_secs_per_unit`、`overdue_rate`、`exception_count`、`exception_rate` 都记为 `0`
- `overdue_rate` 与 `exception_rate` 使用 0 到 1 之间的小数表示
- `efficiency_gap` 定义为 `avg_secs_per_unit - target_secs_per_unit`

### 3. `exceptions`

- 第一行必须是表头
- 列严格为：
  - `event_id`
  - `shift_id`
  - `picker_id`
  - `issue_type`
  - `overdue_flag`
  - `exception_flag`
  - `exception_reason`
  - `units_picked`
  - `active_seconds`
- 仅保留 `overdue_flag = Y` 或 `exception_flag = Y` 的事件
- 行顺序与 `picking_events.csv` 中出现顺序一致
- `issue_type` 规则：
  - 同时超时且异常时写 `overdue+exception`
  - 仅超时时写 `overdue`
  - 仅异常时写 `exception`

### 4. `dashboard`

- 第一行必须是表头，列严格为 `metric`、`value`
- 数据行顺序固定为：
  - `total_shifts`
  - `total_units`
  - `weighted_avg_secs_per_unit`
  - `overall_overdue_rate`
  - `overall_exception_rate`
  - `slowest_shift`
  - `highest_overdue_rate_shift`
- `value` 列必须使用工作表公式
- `weighted_avg_secs_per_unit` 按总活跃秒数除以总件数计算
- `overall_overdue_rate` 按总超时事件数除以总事件数计算
- `overall_exception_rate` 按总异常事件数除以总事件数计算
- `slowest_shift` 指 `avg_secs_per_unit` 最大的班次
- `highest_overdue_rate_shift` 指 `overdue_rate` 最大的班次
- 如果 `slowest_shift` 或 `highest_overdue_rate_shift` 出现并列，选择在 `shifts.csv` 中更早出现的班次
- 如果总件数为 `0`，`weighted_avg_secs_per_unit` 记为 `0`
- 如果总事件数为 `0`，`overall_overdue_rate` 与 `overall_exception_rate` 都记为 `0`

不要生成额外工作表、额外列、说明文字或辅助区域。
