你需要对一个生物反应器批次的温度控制恢复过程做离线审查，不需要重新运行仿真，只需要分析现有过程日志并输出 YAML 总结。

可用输入：
- `thermal_audit_plan.yaml`：反应器批次信息、容差带、两个设定值切换事件和各自的判定阈值。
- `reactor_runs/batch_bt2403_temperature_trace.csv`

日志包含这些列：
- `time_min`
- `setpoint_c`
- `broth_temp_c`
- `jacket_temp_c`
- `steam_valve_pct`
- `phase`

请创建 `/root/thermal_recovery_summary.yaml`，并满足下面要求：

1. 只按 `thermal_audit_plan.yaml` 中 `events` 定义的两个切换事件做审查，每个事件只使用各自 `evaluation_window_min` 内的样本。
2. `overshoot_c` 的计算方式：
   - `heatup` 事件：`max(broth_temp_c - target_setpoint_c, 0)`
   - `cooldown` 事件：`max(target_setpoint_c - broth_temp_c, 0)`
3. `settling_time_min`：从 `switch_time_min` 开始，找到 `broth_temp_c` 首次进入 `target_setpoint_c ± tolerance_band_c` 且之后在该事件剩余评估窗口内始终保持在带内的时刻；结果写成相对 `switch_time_min` 的分钟数。
4. `steady_state_error_c`：取该事件评估窗口最后 `steady_state_window_min` 分钟内 `broth_temp_c` 的平均值，与 `target_setpoint_c` 做绝对误差。
5. `out_of_tolerance_duration_min`：在该事件评估窗口内，统计 `|broth_temp_c - target_setpoint_c| > tolerance_band_c` 的总采样分钟数。
6. 所有数值保留两位小数。
7. 每个事件都要根据 `limits` 中四个阈值计算 `pass_count`，并给出 `status`：
   - 四项都满足时写 `pass`
   - 否则写 `fail`
8. 输出 YAML 顶层键必须严格为：
   - `audit`
   - `events`
   - `overall`

其中：

- `audit` 必须包含：
  - `reactor_id`
  - `batch_id`
  - `tolerance_band_c`
  - `sample_period_min`
- `events` 必须按 `thermal_audit_plan.yaml` 中事件顺序输出；每个事件对象必须包含：
  - `event_id`
  - `phase`
  - `direction`
  - `switch_time_min`
  - `target_setpoint_c`
  - `metrics`
  - `limits`
  - `pass_count`
  - `status`
- `metrics` 必须严格包含：
  - `overshoot_c`
  - `settling_time_min`
  - `steady_state_error_c`
  - `out_of_tolerance_duration_min`
- `overall` 必须包含：
  - `passed_events`
  - `total_events`
  - `requires_investigation`
  - `worst_event`
  - `largest_overshoot_event`

额外规则：
- `requires_investigation` 只要有任一事件 `status` 为 `fail` 就必须为 `true`。
- `worst_event` 选择 `pass_count` 最低的事件；如果并列，选择 `overshoot_c` 更大的那个。
- `largest_overshoot_event` 选择 `overshoot_c` 最大的事件。

示例结构：

```yaml
audit:
  reactor_id: BR-07
  batch_id: BT-2403
  tolerance_band_c: 0.25
  sample_period_min: 1.0
events:
  - event_id: nutrient_shift_heatup
    phase: nutrient_shift
    direction: heatup
    switch_time_min: 18.0
    target_setpoint_c: 37.0
    metrics:
      overshoot_c: 0.32
      settling_time_min: 15.0
      steady_state_error_c: 0.0
      out_of_tolerance_duration_min: 10.0
    limits:
      overshoot_c_max: 0.4
      settling_time_min_max: 15.0
      steady_state_error_c_max: 0.12
      out_of_tolerance_duration_min_max: 10.0
    pass_count: 4
    status: pass
overall:
  passed_events: 1
  total_events: 2
  requires_investigation: true
  worst_event: induction_coolback
  largest_overshoot_event: induction_coolback
```
