你需要实现一个储液罐液位闭环控制仿真。系统只有一个储液罐和一台可调泵，需要在进流量扰动、重力泄流和泵送速率限制下，把液位稳定在固定目标附近，并输出调参结果、完整时序数据和简短性能报告。

可用输入：
- `tank_config.yaml`：储液罐几何参数、泵约束、初始控制参数、采样时间和名义工况。
- `inflow_profile.csv`：已经展开到逐采样的进流量序列，列为 `time_s,inflow_lps`。

请完成以下文件：

1. `pid_controller.py`
- 实现离散 PID 控制器。
- 类名：`PIDController`
- 构造函数：`__init__(self, kp, ki, kd, output_min=None, output_max=None, integral_limit=None)`
- 方法：
  - `reset()`
  - `compute(error, dt) -> float`

2. `tank_controller.py`
- 实现液位控制器。
- 类名：`TankLevelController`
- 构造函数：`__init__(self, config)`，其中 `config` 来自 `tank_config.yaml` 与最终调参结果。
- 方法：
  - `compute(target_level_m, actual_level_m, inflow_lps, dt) -> tuple`
- 返回 `(requested_pump_lps, level_error_m)`。
- `requested_pump_lps` 必须满足配置中的泵流量上下限。

3. `simulate_tank.py`
- 运行完整仿真。
- 运行时必须从 `tank_tuning.yaml` 读取最终 PID 参数，不要把最终参数硬编码在脚本里。
- `inflow_profile.csv` 已经是逐采样数据，不要再做额外重采样。
- 使用下面这个简化液位模型，不要替换为别的过程模型：

```text
pump_step = clip(requested_pump_lps - actual_pump_lps, -pump_ramp_limit_lps_per_s * dt, pump_ramp_limit_lps_per_s * dt)
next_actual_pump_lps = clip(actual_pump_lps + pump_step, min_pump_lps, max_pump_lps)
gravity_outflow_lps = outlet_coeff_lps_per_sqrt_m * sqrt(max(actual_level_m, 0.0))
total_outflow_lps = next_actual_pump_lps + gravity_outflow_lps
next_level_m = clip(
    actual_level_m + ((inflow_lps - total_outflow_lps) / tank_area_m2) * dt,
    min_level_m,
    max_level_m,
)
```

- 输出 `tank_level_response.csv`，列顺序必须严格为：

```text
time_s,target_level_m,actual_level_m,inflow_lps,requested_pump_lps,actual_pump_lps,level_error_m
```

- 该文件必须包含 241 行数据，对应 `0.0s` 到 `120.0s`（含端点）的完整轨迹。

4. `tank_tuning.yaml`
- 保存你调好的控制参数和关键指标，格式如下：

```yaml
pid:
  kp: <value>
  ki: <value>
  kd: <value>
metrics:
  initial_recovery_mae: <value>
  surge_recovery_mae: <value>
  final_window_mae: <value>
  peak_level_m: <value>
```

参数范围要求：
- `kp` 在 `(0, 10)`
- `ki` 在 `[0, 5)`
- `kd` 在 `[0, 5)`
- 最终参数必须不同于 `tank_config.yaml` 里的初始值

5. `level_control_report.md`
- 需要包含这些主题：
  - 液位平衡模型与控制器设计
  - 参数调节过程与最终参数
  - 进流量扰动、泵速率限制和末段稳定性的结果分析

性能目标：
- 初始恢复窗口（`15s` 到 `25s`）平均绝对液位误差 < `0.08 m`
- 大扰动恢复窗口（`54s` 到 `66s`）平均绝对液位误差 < `0.10 m`
- 末段平衡窗口（`100s` 到 `120s`）平均绝对液位误差 < `0.03 m`
- 最高液位 < `1.95 m`
- `actual_pump_lps` 必须始终满足配置中的泵流量上下限
- 相邻采样点的 `actual_pump_lps` 变化量绝对值必须不超过 `0.40 L/s`
- `actual_level_m` 必须始终保持在配置给出的液位上下限内

提示：
- 这是一个标准离散时间过程控制问题，重点是液位误差闭环调节、进流量扰动恢复，以及执行器速率限制下的稳定性。
- `inflow_profile.csv` 已经给出逐采样序列，不需要自己生成额外输入。
