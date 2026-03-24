你需要实现一个温室温度控制仿真。温室种植区只有单一区域，需要在 6 小时天气扰动和加热功率上限下，把区域温度稳定在固定设定值附近，并输出控制日志、调参文件和简短说明。

可用输入：
- `greenhouse_config.yaml`：温室热惯性参数、初始控制参数、采样周期和约束。
- `weather_profile.csv`：已经展开到逐分钟的天气序列，列为 `time_min,outside_temp_c,solar_gain_kw`。

请完成以下文件：

1. `pid_controller.py`
- 实现离散 PID 控制器。
- 类名：`PIDController`
- 构造函数：`__init__(self, kp, ki, kd, output_min=None, output_max=None, integral_limit=None)`
- 方法：
  - `reset()`
  - `compute(error, dt) -> float`

2. `greenhouse_controller.py`
- 实现温室温度控制器。
- 类名：`GreenhouseTemperatureController`
- 构造函数：`__init__(self, config)`，其中 `config` 来自 `greenhouse_config.yaml` 与最终调参结果。
- 方法：
  - `compute(setpoint_temp, zone_temp, outside_temp, solar_gain_kw, dt_minutes) -> tuple`
- 返回 `(heater_power_kw, temp_error)`。
- `heater_power_kw` 必须满足配置中的输出上下限。

3. `simulate_greenhouse.py`
- 运行完整仿真。
- 运行时必须从 `greenhouse_tuning.yaml` 读取最终参数，不要把最终参数硬编码在脚本里。
- `weather_profile.csv` 已经是逐分钟数据，不要再做额外重采样。
- 使用下面这个简化热模型，不要替换为别的模型：

```text
heat_exchange_kw = heat_loss_coeff_kw_per_c * (zone_temp - outside_temp)
net_heat_kw = heater_power_kw + solar_gain_kw - heat_exchange_kw
next_zone_temp = zone_temp + (net_heat_kw / thermal_capacity_kwh_per_c) * (dt_minutes / 60.0)
```

- 输出 `greenhouse_temperature_log.csv`，列顺序必须严格为：

```text
time_min,setpoint_temp,zone_temp,outside_temp,solar_gain_kw,heater_power_kw,net_heat_kw,temp_error
```

- 该文件必须包含 361 行数据，对应 `0` 到 `360` 分钟（含端点）的完整轨迹。

4. `greenhouse_tuning.yaml`
- 保存你调好的控制参数和关键指标，格式如下：

```yaml
pid:
  kp: <value>
  ki: <value>
  kd: <value>
metrics:
  settling_minute: <value>
  cold_snap_max_error: <value>
  solar_overshoot: <value>
  final_window_mae: <value>
```

参数范围要求：
- `kp` 在 `(0, 10)`
- `ki` 在 `[0, 5)`
- `kd` 在 `[0, 5)`
- 最终参数必须不同于 `greenhouse_config.yaml` 里的初始值

5. `climate_notes.md`
- 需要包含这些主题：
  - 热模型与控制器设计
  - 参数调节过程与最终参数
  - 冷空气、日照增益和末段稳定性的结果分析

性能目标：
- 必须在 `80 min` 前首次进入并连续保持 `20 min` 的 `±0.4 C` 稳定带
- 冷空气窗口（`120 min` 到 `180 min`）最大绝对温度误差 < `0.20 C`
- 强日照窗口（`240 min` 到 `300 min`）最大超调量 < `0.35 C`
- 末段稳定窗口（`330 min` 到 `360 min`）平均绝对温度误差 < `0.18 C`
- `heater_power_kw` 必须始终满足配置中的功率上下限

提示：
- 这是一个标准离散时间闭环控制问题，重点是热惯性、外界温差引起的被动换热，以及扰动下的超调抑制。
- `weather_profile.csv` 已经给出逐分钟天气，不需要自己生成额外输入。
