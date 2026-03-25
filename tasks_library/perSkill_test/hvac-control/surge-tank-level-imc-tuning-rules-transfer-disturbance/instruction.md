你要补一份缓冲罐液位回路的扰动恢复报告。对象线性化参数、阀门限制和扰动时间表都已经给定，不需要做辨识；你需要比较候选闭环时间常数，计算 PI 参数，并用给定仿真器生成扰动恢复过程和液位稳定性结论。

输入资产：

- `/root/surge_tank_case.json`：包含案例编号、一阶对象参数 `K` 和 `tau_min`、液位设定点、阀门上下限、候选 `lambda`、仿真步长和验收阈值。
- `/root/disturbance_schedule.csv`：给出进料扰动的分段时间表，列为 `segment_id,start_min,end_min,disturbance_percent`。
- `/root/surge_tank_simulator.py`：提供可直接导入的闭环仿真逻辑。

对每个候选 `lambda_min`，按下面公式计算 PI 参数：

- `Kp = tau / (K * lambda)`
- `Ki = 1 / (K * lambda)`
- `Kd = 0`

然后使用给定仿真器评估整个扰动恢复过程。指标定义按下面规则执行：

- `recovery_time_min`：最后一个非零扰动区间结束后，液位首次回到 `stability_band_percent` 内且之后始终留在带内的时间；如果直到仿真结束都未满足，写 `null`
- `peak_rebound_above_setpoint_percent`：最后一个非零扰动区间结束之后，液位高于设定点的最大幅度；若没有高于设定点，写 `0`
- `lowest_level_percent`：整个仿真窗口中的最低液位
- `max_valve_percent`：整个仿真窗口中的最大阀位
- `min_valve_percent`：整个仿真窗口中的最小阀位
- `final_error_percent`：`setpoint_level_percent - final_level_percent`

候选方案的选择规则必须固定为：

- 先判断每个候选方案是否同时满足 `acceptance` 中的全部阈值
- 在所有满足阈值的方案里，选择 `lambda_min` 最大的那个，代表更保守的恢复整定

把结果写到 `/root/surge_tank_level_report.json`。文件必须是一个 JSON 对象，至少包含这些字段：

- `case_id`：字符串，必须等于输入资产中的 `case_id`
- `selection_rule`：字符串，描述你执行的候选筛选和保守选择规则
- `process_model`：对象，至少包含 `K` 和 `tau_min`
- `selected_lambda_min`：数值，最终选中的候选值
- `controller`：对象，至少包含 `Kp`、`Ki`、`Kd`
- `selected_metrics`：对象，至少包含：
  - `recovery_time_min`
  - `peak_rebound_above_setpoint_percent`
  - `lowest_level_percent`
  - `max_valve_percent`
  - `min_valve_percent`
  - `final_level_percent`
  - `final_error_percent`
- `candidate_review`：数组，长度必须与输入中的候选 `lambda` 数量一致；每个元素至少包含：
  - `lambda_min`
  - `controller`（含 `Kp`、`Ki`、`Kd`）
  - `metrics`
  - `meets_constraints`
- `recovery_trace`：最终选中方案的完整闭环轨迹数组；每个元素至少包含：
  - `time_min`
  - `level_percent`
  - `setpoint_percent`
  - `valve_percent`
  - `disturbance_percent`
  - `error_percent`
- `stability_report`：对象，至少包含：
  - `disturbance_clear_time_min`
  - `within_band_at_end`
  - `meets_recovery_deadline`
  - `meets_rebound_limit`
  - `narrative`
- `summary`：非空字符串，概括为什么该 `lambda` 既满足恢复要求又足够保守

验收时会核对：

- 每个候选 `lambda` 的 PI 增益是否与给定公式一致
- 是否真的评估了全部候选方案，并按题目要求选择最大的可行 `lambda`
- 选中方案的扰动恢复轨迹和关键指标是否与给定仿真器一致
- 稳定性结论是否与输入阈值和仿真结果一致
