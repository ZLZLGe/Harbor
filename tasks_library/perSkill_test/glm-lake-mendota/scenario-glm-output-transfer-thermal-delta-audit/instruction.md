你接手的是 North Arm Thermal Curtain Pilot 的双情景复核。环境里已经提供了这三个输入文件：

- `/root/data/thermal_baseline_output.nc`
- `/root/data/thermal_intervention_output.nc`
- `/root/config/audit_spec.json`

请生成 `/root/reports/scenario_delta_summary.json`。

按下面规则处理：

1. 从 `audit_spec.json` 读取：
   - `site_name`
   - `simulation_start`
   - `lake_depth_m`
   - `focus_depths_m`
   - `summer_start_date`
   - `summer_end_date`
   - `target_temperature_window_c.min`
   - `target_temperature_window_c.max`
2. 两个 NetCDF 里的 `time` 都表示自 `simulation_start` 起经过的小时数。
3. NetCDF 里的 `z` 是“距湖底的高度”，不是“水面以下深度”；必须先换算成 `depth_from_surface_m = lake_depth_m - z`。
4. 对每个情景、每个时间步、每个关注深度，只在 `z` 和 `temp` 都有效的层里选择代表温度：
   - 选 `depth_from_surface_m` 与该关注深度差值最小的层
   - 如果有并列，选更深的那一层
5. 只使用两个情景都成功提取出代表温度的共同时间步。
6. `monthly_depth_deltas` 的计算规则：
   - 对每个共同时间步，按其日历月份 `YYYY-MM` 和关注深度分组
   - `baseline_mean_temp_c` 为该组内基线情景温度的算术平均
   - `intervention_mean_temp_c` 为该组内干预情景温度的算术平均
   - `delta_c = intervention_mean_temp_c - baseline_mean_temp_c`
   - 输出数组必须先按 `month` 升序，再按 `depth_m` 升序排列
7. `summer_bottom_cooling_c` 的计算规则：
   - 取 `focus_depths_m` 中最大的深度作为底层关注深度
   - 只使用日期落在 `summer_start_date` 到 `summer_end_date`（含首尾）的共同时间步
   - 分别计算该深度上基线和干预情景的夏季平均温度
   - `summer_bottom_cooling_c = baseline_summer_mean_temp_c - intervention_summer_mean_temp_c`
   - 正值表示干预方案更冷
8. 目标温度窗口偏差的计算规则：
   - 如果温度落在 `[target_min, target_max]` 内，偏差记为 `0`
   - 如果温度低于 `target_min`，偏差记为 `target_min - temp`
   - 如果温度高于 `target_max`，偏差记为 `temp - target_max`
9. `closer_to_target_by_depth` 的计算规则：
   - 对每个关注深度，在全部共同时间步上分别计算基线和干预情景的平均偏差
   - 输出 `baseline_mean_abs_deviation_c` 和 `intervention_mean_abs_deviation_c`
   - `preferred_scenario` 取偏差更小的方案：`baseline`、`intervention` 或 `tie`
   - 输出数组必须按 `depth_m` 升序排列
10. `overall_preferred_scenario` 的计算规则：
    - 将每个关注深度的平均偏差等权相加
    - 总和更小的方案胜出，写 `baseline` 或 `intervention`
    - 如果完全相等，写 `tie`

输出 JSON 至少包含这些字段：

- `site_name`
- `focus_depths_m`
- `target_temperature_window_c`
- `monthly_depth_deltas`
- `summer_bottom_depth_m`
- `summer_bottom_cooling_c`
- `closer_to_target_by_depth`
- `overall_preferred_scenario`

其中：

- `site_name` 是字符串。
- `focus_depths_m` 是按升序排列的 JSON 数字数组。
- `target_temperature_window_c` 是对象，且必须包含 JSON 数字字段 `min` 和 `max`。
- `summer_bottom_depth_m` 和 `summer_bottom_cooling_c` 都必须是 JSON 数字。
- `monthly_depth_deltas` 是数组；每个元素都必须包含：
  - `month`
  - `depth_m`
  - `baseline_mean_temp_c`
  - `intervention_mean_temp_c`
  - `delta_c`
- `closer_to_target_by_depth` 是数组；每个元素都必须包含：
  - `depth_m`
  - `baseline_mean_abs_deviation_c`
  - `intervention_mean_abs_deviation_c`
  - `preferred_scenario`
- `month` 使用 `YYYY-MM`。
- `preferred_scenario` 和 `overall_preferred_scenario` 只能是 `baseline`、`intervention` 或 `tie`。

只要最终 JSON 满足上述契约即可，字段顺序不限。
