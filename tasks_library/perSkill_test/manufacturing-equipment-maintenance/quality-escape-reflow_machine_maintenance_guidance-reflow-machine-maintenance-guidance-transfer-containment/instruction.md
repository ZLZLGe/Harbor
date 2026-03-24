你需要把回流炉知识迁移到质量逃逸应急场景，输出一张单一 JSON 遏制卡。

可用输入文件都在 `/app/data/` 下：

- `escape_handbook.pdf`：回流工艺与维护手册。
- `incident_context.json`：事件编号、产线和动作卡固定上下文。
- `incident_runs.csv`：批次级 run 记录，包含 lot、气氛、氧含量、液相线和缺陷趋势。
- `defect_distribution.csv`：AOI/目检缺陷分布。
- `incident_traces.csv`：多热电偶温度曲线。
- `mes_unit_history.csv`：MES 单板流转和当前库存位置。

请生成且只生成 `/app/output/defect_containment_card.json`。

要求：

1. 先从手册中提取并使用这些定义，不要猜测：
   - 更适合作为单一代表测点的热电偶角色。
   - 预热斜率的温度区间。
   - 最大预热斜率上限。
   - TAL 的窗口上下限。
   - 峰值温度相对液相线的最低裕量。
   - `N2_full` 与 `N2_mixed` 的氧含量上限。
2. 先识别 `escape_runs`。只有同时满足以下条件的 run 才算质量逃逸 run：
   - `incident_runs.csv` 中 `defect_trend == "up"`
   - `defect_distribution.csv` 中该 run 在 `AOI` 和 `VISUAL` 两个检验站、且缺陷类型属于 `insufficient_solder`、`head_in_pillow`、`voiding`、`dull_joints`、`bridging`、`solder_balls`、`tombstone` 的 `defect_count` 合计至少 20
3. 对每个 `escape_run`，只使用你选定的代表热电偶计算：
   - `ramp_c_per_s`
   - `tal_s`
   - `peak_temp_c`
   - `required_min_peak_c`
4. 每个 `escape_run` 的 `dominant_defect` 必须来自 `defect_distribution.csv`：
   - 汇总该 run 全部检验站的 `defect_count`
   - 取计数最高的 `defect_type`
   - 如并列，取字典序最小的值
5. `suspected_failure_mode` 必须按以下优先级判定：
   - `center_zone_heat_loss`：支持 run 为同时满足 `tal_s < tal_window_s[0]`、`peak_temp_c < required_min_peak_c`，且 `dominant_defect` 属于 `insufficient_solder`、`head_in_pillow`、`voiding`、`dull_joints` 的 `escape_runs`；若支持 run 至少 2 个，则选择该模式
   - `nitrogen_path_leak`：支持 run 为 `gas_mode != "Air"`、`o2_ppm_reflow` 超过对应气氛上限，且 `dominant_defect` 属于 `insufficient_solder`、`head_in_pillow`、`voiding`、`dull_joints` 的 `escape_runs`；若支持 run 至少 2 个，则选择该模式
   - `entry_ramp_overshoot`：支持 run 为 `ramp_c_per_s > max_ramp_c_per_s`，且 `dominant_defect` 属于 `bridging`、`solder_balls`、`tombstone` 的 `escape_runs`；若支持 run 至少 1 个，则选择该模式
   - 否则使用 `recipe_loading_shift`，其支持 run 为全部 `escape_runs`
6. `suspected_failure_mode.priority_subsystem` 只允许使用：
   - `center_heating_zones`
   - `nitrogen_delivery_path`
   - `entry_ramp_section`
   - `loaded_profile_review`
   其中它必须和选中的模式一一对应。
7. `suspected_failure_mode.confidence` 规则：
   - 支持 run 数量 >= 2 时为 `high`
   - 支持 run 数量 == 1 时为 `medium`
   - 否则为 `low`
8. `containment_scope` 必须只基于选中模式的 `trigger_run_ids`：
   - `affected_run_ids` 为 `trigger_run_ids` 升序
   - `affected_lot_ids` 为这些 run 对应 lot 的去重升序列表
   - `serial_span` 为 `mes_unit_history.csv` 中这些 run 的最小和最大 `panel_sn`
   - `panels_to_hold` 为这些 run 中 `disposition != "shipped"` 的 panel 数量
   - `shipped_panels` 为这些 run 中 `disposition == "shipped"` 的 panel 数量
   - `hold_locations` 为这些 run 中 `disposition != "shipped"` 的 `current_location` 去重升序列表
9. `immediate_actions` 必须正好 3 条，`step` 必须为 1 到 3 连续整数，`owner_role` 必须依次是：
   - `quality_engineer`
   - `line_lead`
   - `maintenance_technician`
10. `technician_action_card` 必须和选中的模式一致，且所有数组按字符串升序，所有浮点数保留 2 位小数。

输出格式必须严格如下：

```json
{
  "incident_id": "",
  "line_id": "",
  "window_reference": {
    "reference_tc_role": "",
    "preheat_band_c": [0.0, 0.0],
    "max_ramp_c_per_s": 0.0,
    "tal_window_s": [0.0, 0.0],
    "peak_margin_above_liquidus_c": 0.0
  },
  "escape_run_analysis": [
    {
      "run_id": "",
      "lot_id": "",
      "dominant_defect": "",
      "escape_defect_total": 0,
      "ramp_c_per_s": 0.0,
      "tal_s": 0.0,
      "peak_temp_c": 0.0,
      "required_min_peak_c": 0.0,
      "signal_flags": {
        "ramp_violation": false,
        "tal_low": false,
        "peak_low": false,
        "oxygen_over_limit": false
      }
    }
  ],
  "suspected_failure_mode": {
    "mode_code": "center_zone_heat_loss",
    "priority_subsystem": "center_heating_zones",
    "confidence": "high",
    "trigger_run_ids": [""],
    "evidence": {
      "dominant_defects": [""],
      "tal_below_runs": [""],
      "peak_below_runs": [""],
      "ramp_violation_runs": [""],
      "oxygen_over_limit_runs": [""]
    }
  },
  "containment_scope": {
    "affected_run_ids": [""],
    "affected_lot_ids": [""],
    "serial_span": ["", ""],
    "panels_to_hold": 0,
    "shipped_panels": 0,
    "hold_locations": [""]
  },
  "immediate_actions": [
    {
      "step": 1,
      "owner_role": "quality_engineer",
      "action": "",
      "reason": ""
    }
  ],
  "technician_action_card": {
    "subsystem": "center_heating_zones",
    "inspection_points": [""],
    "parameter_checks": [""],
    "release_condition": ""
  }
}
```
