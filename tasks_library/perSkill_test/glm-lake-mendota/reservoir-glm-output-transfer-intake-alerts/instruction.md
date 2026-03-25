你在接手一份名为 Silverwood Reservoir 的热分层巡检结果。环境里已经提供了这两个输入文件：

- `/root/data/silverwood_reservoir_output.nc`
- `/root/config/intake_profile.json`

请生成 `/root/reports/intake_alerts.json`，用于汇总指定取水口深度处的高温告警时段。

按下面规则处理：

1. 从 `intake_profile.json` 读取：
   - `reservoir_name`
   - `simulation_start`
   - `lake_depth_m`
   - `intake_depth_m`
   - `alert_threshold_c`
2. NetCDF 里的 `time` 表示自 `simulation_start` 起经过的小时数。
3. NetCDF 里的 `z` 是“距水底的高度”，不是“水面以下深度”；必须先换算成 `depth_from_surface_m = lake_depth_m - z`。
4. 对每一个模型时间步，在所有有效层里选出 `depth_from_surface_m` 与 `intake_depth_m` 差值最小的那一层，取该层温度作为该时刻的取水温度；如果有并列，取更深的那一层。
5. 取水温度严格大于 `alert_threshold_c` 时，记为告警样本。
6. 将按时间排序后的连续告警样本合并成一个告警时段。这里的“连续”指它们在提取后的取水温度时间序列中相邻，没有夹着非告警时间步。
7. `time_step_hours` 取提取后时间序列相邻两个时间戳的固定间隔小时数；每个告警时段的 `duration_hours = sample_count * time_step_hours`。
8. `alerts` 必须按 `start_time` 升序排列。
9. `longest_alert` 取所有告警时段中 `duration_hours` 最大的那个；如果并列，取 `peak_temperature_c` 更高的；如果还并列，取更早开始的那个。
10. 如果不存在任何告警时段，输出空数组 `alerts`，并把 `longest_alert` 设为 `null`。

输出 JSON 至少包含这些字段：

- `reservoir_name`
- `intake_depth_m`
- `alert_threshold_c`
- `time_step_hours`
- `evaluated_sample_count`
- `peak_temperature_c`
- `alerts`
- `longest_alert`

其中：

- `reservoir_name` 是字符串。
- `intake_depth_m`、`alert_threshold_c`、`time_step_hours`、`peak_temperature_c` 都必须是 JSON 数字。
- `evaluated_sample_count` 必须是 JSON 整数。
- `alerts` 是数组；每个元素都必须包含：
  - `start_time`
  - `end_time`
  - `sample_count`
  - `duration_hours`
  - `peak_temperature_c`
- `start_time` 和 `end_time` 使用不带时区的 ISO 8601 字符串，例如 `2009-07-01T12:00:00`。
- `sample_count` 必须是 JSON 整数，其余数值字段必须是 JSON 数字。

只要最终 JSON 满足上述契约即可，字段顺序不限。
