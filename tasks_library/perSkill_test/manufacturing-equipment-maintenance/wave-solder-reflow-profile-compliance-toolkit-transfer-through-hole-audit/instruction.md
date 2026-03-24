你在支持一条通孔插件线做波峰焊 lot 审核。请综合工艺手册、lot 清单、热电偶数据、线速日志和桥连/虚焊缺陷记录，输出一份唯一的审核结果文件。

可用输入文件都在 `/app/data/`:
- `wave_solder_handbook.pdf`
- `lot_manifest.csv`
- `wave_thermocouples.csv`
- `line_speed_log.csv`
- `defect_ledger.csv`

请生成 `/app/output/wave_solder_profile_audit.yaml`，并满足以下要求：

1. 必须先从手册中提取以下规则，不能猜测：
- 预热斜率计算的温度区间
- 允许的最大预热斜率
- 入波前板面温度窗口，以及传感器选取规则
- 过波接触时间阈值、窗口，以及传感器选取规则
- 有效接触长度与可接受输送速度窗口
- 推荐参数组合的目标中心值
- `failure_reasons` 的固定输出顺序

2. 计算规则：
- `max_preheat_ramp_c_per_s`：仅使用 `sensor_group = "top_preheat"` 的数据；每个热电偶按时间排序后，只对两个端点都落在预热温区内的相邻采样段计算斜率，取 lot 级最大值；若并列，lot 级明细里不需要额外暴露该热电偶。
- `board_entry_temp_c`：仅使用 `record_type = "entry_snapshot"` 且 `sensor_group = "entry_top"` 的记录，取温度最低的热电偶；若温度相同，取字典序更小的 `tc_id`。
- `contact_time_s`：仅使用 `record_type = "wave_trace"` 且 `sensor_group = "wave_contact"` 的记录，以手册给出的接触阈值做线性插值，计算每个热电偶高于阈值的持续时间；取持续时间最长的热电偶；若持续时间相同，取字典序更小的 `tc_id`。
- `actual_speed_cm_min`：取该 lot 在 `line_speed_log.csv` 中所有 `speed_cm_min` 的中位数。
- `thermal_status = "pass"` 仅当预热斜率、入波温度、接触时间三项都满足手册要求。
- `speed_status = "pass"` 仅当 `actual_speed_cm_min` 落在手册速度窗口内。
- `defect_status = "pass"` 仅当 `bridge_count = 0` 且 `insufficient_fill_count = 0`。
- `audit_status = "pass"` 仅当 `thermal_status`、`speed_status`、`defect_status` 都为 `pass`。
- `failure_reasons` 只能从以下 code 中取值，并按固定顺序输出：
  1. `preheat_ramp_exceeds_limit`
  2. `entry_temp_out_of_window`
  3. `contact_time_out_of_window`
  4. `speed_out_of_window`
  5. `bridging_present`
  6. `insufficient_fill_present`
- `qualified_lot_ids` 只包含 `audit_status = "pass"` 的 lots，按 `lot_id` 升序。
- `blocked_lot_ids` 只包含 `audit_status = "fail"` 的 lots，按 `lot_id` 升序。

3. 推荐参数组合：
- 只允许在 `audit_status = "pass"` 的 lots 中汇总。
- 以 `profile_id` 分组，参数字段来自 `lot_manifest.csv`。
- 每个 profile 输出：
  - `qualified_lot_ids`
  - `lot_count`
  - `average_entry_temp_c`
  - `average_contact_time_s`
  - `average_speed_cm_min`
  - `recommended_speed_cm_min`，与 `average_speed_cm_min` 相同
- `recommended_profiles` 的排序规则固定为：
  1. `lot_count` 更高优先
  2. `average_entry_temp_c` 到手册目标中心值的绝对偏差更小优先
  3. `average_contact_time_s` 到手册目标中心值的绝对偏差更小优先
  4. `average_speed_cm_min` 到手册目标中心值的绝对偏差更小优先
  5. `profile_id` 字典序更小优先
- `best_profile_id` 必须等于 `recommended_profiles` 第一项的 `profile_id`；若没有通过的 profile，则为 `null`。

4. 输出要求：
- 所有浮点数保留 2 位小数。
- 所有 lot 列表按 `lot_id` 升序。
- 不要输出 `NaN` 或 `Infinity`，必要时使用 `null`。
- YAML 顶层字段必须与下列结构一致，不要额外添加字段：

```yaml
line_id: WS-7
handbook_limits:
  preheat_temp_min_c: 0.0
  preheat_temp_max_c: 0.0
  max_preheat_ramp_c_per_s: 0.0
  entry_temp_min_c: 0.0
  entry_temp_max_c: 0.0
  contact_time_threshold_c: 0.0
  contact_time_min_s: 0.0
  contact_time_max_s: 0.0
  effective_wave_contact_length_cm: 0.0
  speed_min_cm_min: 0.0
  speed_max_cm_min: 0.0
  target_entry_temp_c: 0.0
  target_contact_time_s: 0.0
  target_speed_cm_min: 0.0
  entry_sensor_rule: lowest_entry_temp_then_smallest_tc_id
  contact_sensor_rule: longest_time_above_threshold_then_smallest_tc_id
qualified_lot_ids: ["LOT-WS-000"]
blocked_lot_ids: ["LOT-WS-001"]
best_profile_id: PRF-A
lots:
  - lot_id: LOT-WS-000
    profile_id: PRF-A
    entry_sensor_id: TOP1
    contact_sensor_id: WAVE1
    max_preheat_ramp_c_per_s: 0.0
    board_entry_temp_c: 0.0
    contact_time_s: 0.0
    actual_speed_cm_min: 0.0
    bridge_count: 0
    insufficient_fill_count: 0
    thermal_status: pass
    speed_status: pass
    defect_status: pass
    audit_status: pass
    failure_reasons: []
recommended_profiles:
  - profile_id: PRF-A
    preheater_top_sp_c: 0.0
    chip_wave_height_mm: 0.0
    lambda_wave_height_mm: 0.0
    lot_count: 0
    qualified_lot_ids: ["LOT-WS-000"]
    average_entry_temp_c: 0.0
    average_contact_time_s: 0.0
    average_speed_cm_min: 0.0
    recommended_speed_cm_min: 0.0
```
