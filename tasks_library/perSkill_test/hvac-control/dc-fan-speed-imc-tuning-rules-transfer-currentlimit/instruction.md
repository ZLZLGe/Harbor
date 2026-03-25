你要给一台直流送风机整理一张转速环整定卡。电机速度模型已经辨识完成，不需要再做实验；你只需要在候选闭环时间常数中找出“最快但不过流”的方案，计算 PI 参数，并给出转速阶跃跟踪检查点。

输入资产：

- `/root/motor_speed_case.toml`：包含案例编号、速度对象参数 `K_rpm_per_amp` 与 `tau_sec`、初始与目标转速、电流上限、候选 `lambda` 和跟踪分析时域。
- `/root/checkpoints_ms.tsv`：列出需要写入跟踪检查点的采样时刻，表头为 `time_ms`。

对每个候选 `lambda_sec`，按下面公式计算 PI 参数：

- `Kp = tau / (K * lambda)`
- `Ki = 1 / (K * lambda)`
- `Kd = 0`

闭环速度与电流预测必须按下面解析式计算，其中 `t` 的单位是秒：

- `predicted_speed_rpm(t) = target_speed_rpm - (target_speed_rpm - initial_speed_rpm) * exp(-t / lambda_sec)`
- `predicted_current_a(t) = (target_speed_rpm + (target_speed_rpm - initial_speed_rpm) * (tau_sec / lambda_sec - 1) * exp(-t / lambda_sec)) / K_rpm_per_amp`
- `tracking_error_rpm(t) = target_speed_rpm - predicted_speed_rpm(t)`

对当前这个正向转速阶跃，候选方案的峰值电流必须按下面规则计算：

- `peak_current_a = max(target_speed_rpm / K_rpm_per_amp, (initial_speed_rpm + (target_speed_rpm - initial_speed_rpm) * tau_sec / lambda_sec) / K_rpm_per_amp)`

候选筛选和最终选择规则必须固定为：

- 对每个候选 `lambda_sec` 计算 `peak_current_a`
- 当且仅当 `peak_current_a <= current_limit_a` 时，该候选视为可行
- 在所有可行候选中，选择 `lambda_sec` 最小的那个，代表最快但不过流

把结果写到 `/root/motor_speed_tuning_card.json`。文件必须是一个 JSON 对象，至少包含这些字段：

- `case_id`：字符串，必须等于输入资产中的 `case_id`
- `selection_rule`：字符串，描述你执行的最快可行选择逻辑
- `process_model`：对象，至少包含 `K_rpm_per_amp` 和 `tau_sec`
- `operating_point`：对象，至少包含 `initial_speed_rpm`、`target_speed_rpm`、`current_limit_a`
- `selected_lambda_sec`：数值，最终选中的候选值
- `controller`：对象，至少包含 `Kp`、`Ki`、`Kd`
- `candidate_review`：数组，长度必须与候选 `lambda` 数量一致；每个元素至少包含：
  - `lambda_sec`
  - `controller`（含 `Kp`、`Ki`、`Kd`）
  - `steady_state_current_a`
  - `peak_current_a`
  - `within_current_limit`
- `tracking_summary`：对象，至少包含：
  - `response_horizon_sec`
  - `steady_state_current_a`
  - `peak_current_a`
  - `current_margin_a`
  - `final_speed_rpm`
  - `final_error_rpm`
  - `steady_state_error_rpm`
  - `checkpoints`
- `summary`：非空字符串，概括为什么该方案既最快又满足电流上限

其中 `tracking_summary.checkpoints` 必须是数组，长度必须与 `/root/checkpoints_ms.tsv` 中的时刻数量一致；每个元素至少包含：

- `time_ms`
- `predicted_speed_rpm`
- `predicted_current_a`
- `tracking_error_rpm`

另外还需要满足：

- `tracking_summary.steady_state_error_rpm` 必须写 `0.0`，因为 PI 闭环对该一阶模型的稳态误差为零
- `tracking_summary.current_margin_a = current_limit_a - peak_current_a`
- `tracking_summary.final_speed_rpm`、`final_error_rpm` 必须使用 `response_horizon_sec` 对应的解析值

验收时会核对：

- 每个候选 `lambda` 的 PI 增益是否与给定公式一致
- 是否真的按峰值电流约束筛选并选择最小可行 `lambda`
- 跟踪检查点、峰值电流、最终误差和电流裕量是否与解析式一致
- 输出中的关键信息是否与输入资产一致
