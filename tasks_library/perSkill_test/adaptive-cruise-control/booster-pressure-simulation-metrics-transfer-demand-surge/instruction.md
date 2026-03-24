你需要对一个增压泵站在用水突增工况下的稳压表现做离线复核，不需要重新运行仿真，只需要分析现有日志并输出指标表。

可用输入：
- `pressure_review.yaml`：泵站目标压力、突增事件时间窗、低压阈值、排名规则和候选方案顺序。
- `pressure_runs/legacy_valve_trim.csv`
- `pressure_runs/balanced_vfd_pid.csv`
- `pressure_runs/buffer_tank_assist.csv`

每个日志都包含这些列：
- `time_s`
- `demand_lps`
- `discharge_pressure_bar`
- `pump_speed_pct`
- `bypass_valve_pct`

请创建 `/root/pressure_surge_metrics.csv`，并满足下面要求：

1. 只按 `pressure_review.yaml` 中 `candidates` 的顺序读取候选方案，并使用同一个 `evaluation_window_s`、`dip_search_window_s`、`steady_state_window_s` 和 `limits` 计算指标。
2. `rise_time_s` 的计算方式：
   - 先在 `dip_search_window_s` 内找到 `discharge_pressure_bar` 的最低点，记为 `minimum_pressure_bar`。
   - 令 `recovery_span = target_pressure_bar - minimum_pressure_bar`。
   - 只使用从最低点开始、且仍位于 `evaluation_window_s` 内的样本，找到压力首次达到 `minimum_pressure_bar + 10% * recovery_span` 和首次达到 `minimum_pressure_bar + 90% * recovery_span` 的时刻。
   - `rise_time_s` 等于这两个时刻之差。
3. `overshoot_pct`：只在 `evaluation_window_s` 内统计，按 `max(discharge_pressure_bar - target_pressure_bar, 0) / target_pressure_bar * 100` 计算最大超调百分比。
4. `steady_state_error_bar`：在 `steady_state_window_s` 内取 `discharge_pressure_bar` 的平均值，与 `target_pressure_bar` 做绝对误差。
5. `low_pressure_duration_s`：在 `evaluation_window_s` 内，统计 `discharge_pressure_bar < low_pressure_threshold_bar` 的总采样时长。
6. `thresholds_passed`：按 `limits` 中四个阈值分别判断是否通过，并写成 `x/4`。
7. `rank` 从 `1` 开始，排序规则严格为：
   - `thresholds_passed` 更多优先
   - `low_pressure_duration_s` 更短优先
   - `steady_state_error_bar` 更小优先
   - `overshoot_pct` 更小优先
   - 若仍并列，按 `candidate` 字典序升序
8. 所有数值保留两位小数。
9. 输出 CSV 必须严格使用以下列顺序，并按 `rank` 升序写出：

`rank,candidate,rise_time_s,overshoot_pct,steady_state_error_bar,low_pressure_duration_s,thresholds_passed`

示例结构：

```csv
rank,candidate,rise_time_s,overshoot_pct,steady_state_error_bar,low_pressure_duration_s,thresholds_passed
1,balanced_vfd_pid,6.00,0.80,0.01,4.50,4/4
2,buffer_tank_assist,11.00,0.00,0.04,4.00,3/4
```
