你需要实现一个无人机定高仿真。飞行器只考虑垂直方向运动，需要在目标高度切换和阵风扰动下保持高度稳定，并输出调参结果、完整飞行轨迹和分析报告。

可用输入：
- `drone_config.yaml`：无人机垂直动力学参数、初始控制参数、采样时间和约束。
- `mission_profile.csv`：目标高度分段表，列为 `segment_id,start_time,end_time,target_altitude_m`。
- `gust_windows.csv`：阵风时间窗，列为 `start_time,end_time,gust_accel_mps2`，表示附加到垂直动力学上的加速度扰动。

请完成以下文件：

1. `pid_controller.py`
- 实现离散 PID 控制器。
- 类名：`PIDController`
- 构造函数：`__init__(self, kp, ki, kd, output_min=None, output_max=None, integral_limit=None)`
- 方法：
  - `reset()`
  - `compute(error, dt) -> float`

2. `altitude_controller.py`
- 实现定高控制器。
- 类名：`AltitudeHoldController`
- 构造函数：`__init__(self, config)`，其中 `config` 来自 `drone_config.yaml`
- 方法：
  - `compute(target_altitude, actual_altitude, vertical_speed, dt) -> tuple`
- 返回 `(collective_cmd, altitude_error)`。
- `collective_cmd` 必须满足配置中的输出上下限。

3. `simulate_altitude.py`
- 运行完整仿真。
- 运行时必须从 `altitude_tuning.yaml` 读取最终参数，不要把最终参数硬编码在脚本里。
- 需要把 `mission_profile.csv` 和 `gust_windows.csv` 按 `dt=0.2s` 展开成完整时序，得到 `0.0s` 到 `90.0s` 的仿真序列。
- 使用下面这个简化垂直动力学模型，不要替换为别的模型：

```text
net_vertical_accel = collective_cmd + gust_accel - vertical_damping * vertical_speed
next_vertical_speed = clip(vertical_speed + net_vertical_accel * dt, max_sink_rate_mps, max_climb_rate_mps)
next_altitude = max(0.0, actual_altitude + next_vertical_speed * dt)
```

- 输出 `altitude_hold_trace.csv`，列顺序必须严格为：

```text
time,target_altitude,actual_altitude,vertical_speed,collective_cmd,gust_accel,altitude_error
```

- 该文件必须包含 451 行数据，对应 `0.0s` 到 `90.0s`（含端点）的完整轨迹。

4. `altitude_tuning.yaml`
- 保存你调好的控制参数和关键指标，格式如下：

```yaml
pid:
  kp: <value>
  ki: <value>
  kd: <value>
metrics:
  worst_post_gust_mae: <value>
  max_step_window_mae: <value>
  final_hover_mae: <value>
```

参数范围要求：
- `kp` 在 `(0, 10)`
- `ki` 在 `[0, 5)`
- `kd` 在 `[0, 5)`
- 最终参数必须不同于 `drone_config.yaml` 里的初始值

5. `hover_analysis.md`
- 需要包含这些主题：
  - 垂直动力学模型与控制器设计
  - 参数调节过程与最终参数
  - 阵风恢复、高度切换和最终定高窗口的性能结果

性能目标：
- 第 1 次阵风恢复窗口（`10s` 到 `15s`）平均绝对高度误差 < `0.35 m`
- 第 2 次阵风恢复窗口（`37s` 到 `42s`）平均绝对高度误差 < `0.35 m`
- 高度切换后的稳态窗口中，最差平均绝对高度误差 < `0.25 m`
  - 上升窗口：`21s` 到 `30s`
  - 再上升窗口：`66s` 到 `75s`
- 下降后的稳定窗口（`55s` 到 `60s`）平均绝对高度误差 < `0.30 m`
- 最终定高窗口（`84s` 到 `90s`）平均绝对高度误差 < `0.10 m`
- `collective_cmd` 必须始终满足配置中的上下限
- `actual_altitude` 不能低于 `0.0 m`

提示：
- 这是一个标准离散时间闭环控制问题，重点是高度误差建模、阵风扰动抑制和目标高度切换后的恢复。
- `mission_profile.csv` 和 `gust_windows.csv` 都是分段输入，不是已经展开好的逐采样轨迹。
