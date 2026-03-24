你需要把回流炉维护知识迁移到工单分诊场景，生成一个机器级维护优先级看板。

可用输入文件都在 `/app/data/` 下：

- `maintenance_handbook.pdf`：回流炉维护与工艺手册。
- `machine_backlog.csv`：机器级 backlog 台账，包含 PM 逾期、停机时长和热电偶漂移事件。
- `downtime_breakdown.csv`：最近 7 天各机器的停机子系统拆分。
- `recent_runs.csv`：最近两次代表性 run 的机器、气氛、氧含量和缺陷趋势。
- `weekly_traces.csv`：这些 run 的热电偶曲线，包含多个测点角色。

请生成且只生成 `/app/output/maintenance_priority_board.json`。

要求：

1. 先从手册中提取并使用这些定义，不要猜测：
   - 代表整机判断时更适合作为单一代表测点的热电偶角色。
   - 预热斜率使用的温度区间。
   - 最大预热斜率上限。
   - TAL 的窗口上下限。
   - 峰值温度相对液相线的最低裕量。
2. 对每个 run，只使用你选定的代表热电偶计算：
   - 预热阶段最大斜率。
   - TAL。
   - 峰值温度。
3. 再按机器汇总，并严格按下面规则打分：
   - `oxygen_wetting_risk`：若同一机器至少 2 个 run 的 `o2_ppm_reflow` 超过对应气氛上限，且这些 run 的 `dominant_defect` 都属于 `insufficient_solder`、`voiding`、`head_in_pillow`，并且 `defect_trend` 为 `up`，则记 40 分，否则记 0 分。
   - `heat_delivery_risk`：若同一机器至少 2 个 run 同时满足 TAL 低于窗口下限且峰值温度低于最低要求，则记 35 分，否则记 0 分。
   - `ramp_risk`：若同一机器至少 1 个 run 的预热斜率超限，且该 run 的 `dominant_defect` 属于 `bridging`、`solder_balls`、`tombstone`，并且 `defect_trend` 为 `up`，则记 25 分，否则记 0 分。
   - `sensor_instability`：若 `machine_backlog.csv` 中 `tc_drift_events_7d >= 2`，则记 20 分，否则记 0 分。
   - `maintenance_overdue`：若 `maintenance_overdue` 为 1，则记 15 分，否则记 0 分。
   - `downtime_burden`：若 `downtime_minutes_7d >= 120`，则记 10 分，否则记 0 分。
   - `priority_score` 为以上六项之和。
4. 气氛上限固定如下：
   - `N2_full`：500 ppm。
   - `N2_mixed`：1000 ppm。
   - `Air`：不做氧含量超限判定，因此 `over_limit_oxygen_runs` 必须为空数组。
5. `first_check_subsystem` 只允许使用以下枚举值，并按下面优先级判定：
   - 若 `oxygen_wetting_risk > 0`，使用 `nitrogen_delivery_path`
   - 否则若 `heat_delivery_risk > 0`，使用 `center_heating_zones`
   - 否则若 `ramp_risk > 0`，使用 `entry_ramp_section`
   - 否则若 `sensor_instability > 0`，使用 `thermocouple_chain`
   - 否则使用 `planned_pm_window`
6. `priority_band` 只允许使用：
   - `urgent`：`priority_score >= 80`
   - `high`：`50 <= priority_score < 80`
   - `medium`：`25 <= priority_score < 50`
   - `low`：`priority_score < 25`
7. `largest_stop_subsystem` 来自 `downtime_breakdown.csv` 中该机器 `downtime_minutes_7d` 最大的 `subsystem_code`；若并列，取字典序最小的值。
8. `machines` 必须按 `priority_score` 降序排序；若并列按 `machine_id` 升序。`priority_rank` 从 1 开始连续编号。所有数组按字符串升序。所有浮点数保留 2 位小数。
9. `why_this_first` 需要用一句英文说明该机器为什么应该先检查这个子系统，必须和你的分诊结论一致。

输出格式必须严格如下：

```json
{
  "board_name": "weekly_reflow_maintenance_backlog",
  "window_reference": {
    "reference_tc_role": "",
    "preheat_band_c": [0.0, 0.0],
    "max_ramp_c_per_s": 0.0,
    "tal_window_s": [0.0, 0.0],
    "peak_margin_above_liquidus_c": 0.0
  },
  "machines": [
    {
      "priority_rank": 1,
      "machine_id": "",
      "priority_band": "urgent",
      "priority_score": 0.0,
      "first_check_subsystem": "nitrogen_delivery_path",
      "score_breakdown": {
        "oxygen_wetting_risk": 0.0,
        "heat_delivery_risk": 0.0,
        "ramp_risk": 0.0,
        "sensor_instability": 0.0,
        "maintenance_overdue": 0.0,
        "downtime_burden": 0.0
      },
      "evidence": {
        "largest_stop_subsystem": "",
        "downtime_minutes_7d": 0,
        "tc_drift_events_7d": 0,
        "over_limit_oxygen_runs": [""],
        "tal_low_runs": [""],
        "peak_low_runs": [""],
        "ramp_violation_runs": [""],
        "dominant_defects": [""]
      },
      "why_this_first": ""
    }
  ]
}
```
