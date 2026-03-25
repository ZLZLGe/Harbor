你在做一份再热盘管回路的调试记录复核。模型参数已经给定，不需要再做辨识；你的任务是比较 3 组候选闭环时间常数，计算对应的 PI 增益，运行给定离散仿真器，并给出最终推荐方案。

输入资产：

- `/root/reheat_commissioning_case.json`：包含一阶对象参数 `K`、`tau_sec`、初始工况、3 组候选 `lambda_sec`、仿真步长与验收阈值。
- `/root/reheat_loop_simulator.py`：提供可直接导入的离散闭环仿真逻辑。

对每个候选 `lambda_sec`，按下面公式计算 PI 参数：

- `Kp = tau / (K * lambda)`
- `Ki = 1 / (K * lambda)`
- `Kd = 0`

然后用提供的仿真器评估闭环响应。指标定义按下面规则执行：

- `rise_time_sec`：区域温度首次达到设定点变化量 90% 的时间；如果在仿真窗口内未达到，写 `null`
- `overshoot_percent`：`max(0, (max_temp - setpoint) / step_change * 100)`
- `settling_time_sec`：从某个时刻开始，剩余全部采样点都落在 `settling_band_c` 内的最早时间；如果在仿真窗口内未满足，写 `null`
- `max_valve_percent`：轨迹中的最大阀位
- `saturation_ratio`：阀位等于上限 100% 的采样点占比

选择规则必须写死为：

- 先判定每个候选方案是否同时满足 `acceptance` 中列出的全部约束
- 在所有可行方案中，选择 `lambda_sec` 最小的那个

把结果写到 `/root/reheat_loop_design.json`，并且文件必须是一个 JSON 对象，至少包含这些字段：

- `case_id`：字符串，必须等于输入资产中的 `case_id`
- `selection_rule`：字符串，描述你执行的选择规则
- `selected_lambda_sec`：数值，最终选中的候选值
- `controller`：对象，至少包含 `Kp`、`Ki`、`Kd`
- `selected_metrics`：对象，至少包含 `rise_time_sec`、`overshoot_percent`、`settling_time_sec`、`max_valve_percent`、`saturation_ratio`
- `candidates`：长度为 3 的数组；每个元素至少包含：
  - `lambda_sec`
  - `controller`（含 `Kp`、`Ki`、`Kd`）
  - `metrics`
  - `feasible`
- `trajectory`：最终选中方案的完整闭环轨迹数组；每个元素至少包含 `time_sec`、`zone_temp_c`、`setpoint_c`、`valve_percent`、`error_c`
- `summary`：非空字符串，简述为什么选择该方案

验收时会核对：

- 增益是否与给定公式一致
- 是否真的对全部候选方案做了仿真评估
- 选中的方案是否符合输入资产中的约束
- 轨迹和指标是否与给定仿真器一致
