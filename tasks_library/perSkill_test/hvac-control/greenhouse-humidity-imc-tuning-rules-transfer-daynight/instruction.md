你要为温室喷雾增湿回路整理一份昼夜双模式整定方案。对象参数已经给定，不需要再做辨识；你只需要根据给定的一阶模型、候选闭环时间常数和昼夜两套目标，计算 PI 参数并写出 15 分钟闭环湿度摘要。

输入资产：

- `/root/greenhouse_humidity_case.json`：包含案例编号、一阶对象参数 `K` 与 `tau_min`，以及白天/夜间两套初始湿度、目标湿度和候选 `lambda`。
- `/root/summary_minutes.csv`：列出需要写入响应摘要的采样时刻，单位为分钟。

对白天和夜间都按下面公式计算 PI 参数：

- `Kp = tau / (K * lambda)`
- `Ki = 1 / (K * lambda)`
- `Kd = 0`

`lambda` 的选择规则必须固定为：

- 白天模式使用候选列表里最小的 `lambda`，代表偏快响应
- 夜间模式使用候选列表里最大的 `lambda`，代表偏稳响应

闭环湿度摘要必须按下面解析式生成：

- `predicted_humidity_percent(t) = target - (target - initial) * exp(-t / lambda)`
- `error_to_target_percent(t) = target - predicted_humidity_percent(t)`
- `progress_percent_at_horizon = (1 - exp(-15 / lambda)) * 100`

把结果写到 `/root/humidity_controller_plan.json`。文件必须是一个 JSON 对象，至少包含这些字段：

- `case_id`：字符串，必须等于输入资产中的 `case_id`
- `selection_rule`：字符串，描述你执行的昼夜 lambda 选择规则
- `process_model`：对象，至少包含 `K` 和 `tau_min`
- `day_mode`：对象，至少包含：
  - `selected_lambda_min`
  - `controller`（含 `Kp`、`Ki`、`Kd`）
  - `response_summary`
- `night_mode`：对象，至少包含：
  - `selected_lambda_min`
  - `controller`（含 `Kp`、`Ki`、`Kd`）
  - `response_summary`
- `summary`：非空字符串，概括白天为什么更快、夜间为什么更稳

其中每个模式的 `response_summary` 至少包含：

- `duration_min`：必须为 15
- `samples`：数组，长度必须与 `/root/summary_minutes.csv` 中的时刻数量一致；每个元素至少包含：
  - `time_min`
  - `predicted_humidity_percent`
  - `error_to_target_percent`
- `end_humidity_percent`
- `remaining_error_percent`
- `progress_percent_at_horizon`

验收时会核对：

- 昼夜 `lambda` 是否按题目要求分别取最小值与最大值
- PI 增益是否与给定公式一致
- 15 分钟摘要是否按给定解析式和采样时刻生成
- 输出中的关键信息是否与输入资产一致
