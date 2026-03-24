你要为一只蓄水罐做一次开环液位辨识。工艺组准备后续根据你的结果设计液位控制器，但当前只批准做一次进水阀开度阶跃试验；试验如果把液位推到溢流线以上，整次窗口就算报废。

可用环境：
- `reservoir_simulator.py`：蓄水罐与液位传感器仿真器
- `reservoir_profile.json`：可见运行参数，包括采样周期、当前液位和溢流约束

请自行设计并执行一次既安全、又足以看清液位动态的单次阀门阶跃试验，并在 `/root/tank_level_response_fit.json` 输出结果。要求：

1. 试验必须从 0% 进水阀的稳定液位开始，先保留一小段基线数据，再切换到一个固定正开度，并保持到试验结束。
2. 全程液位必须严格低于配置中的溢流液位，不能触发溢流约束。
3. 采样间隔必须固定，原始日志要能清楚反映液位从基线抬升到接近稳态的过程。
4. 基于这次试验数据拟合一个一阶液位模型，给出阀门稳态增益、时间常数，以及该阶跃下预测的最终液位。

`tank_level_response_fit.json` 至少需要包含以下字段：

```json
{
  "excitation_plan": {
    "baseline_duration_sec": 24.0,
    "valve_step_percent": 36.0,
    "sample_interval_sec": 4.0,
    "total_duration_sec": 584.0,
    "overflow_limit_cm": 59.0
  },
  "level_response": [
    {
      "time_s": 0.0,
      "level_cm": 41.5,
      "valve_open_percent": 0.0
    }
  ],
  "identified_model": {
    "steady_gain_cm_per_percent": 0.34,
    "time_constant_sec": 160.0,
    "fit_rmse_cm": 0.08,
    "predicted_final_level_cm": 53.7
  }
}
```

补充要求：
- `level_response` 中每条记录都要包含 `time_s`、`level_cm`、`valve_open_percent`。
- `excitation_plan.total_duration_sec` 必须和原始日志总时长一致。
- `excitation_plan.valve_step_percent` 必须和阶跃后的恒定阀门开度一致。
- `identified_model.fit_rmse_cm` 填写你的拟合误差。

除了 `tank_level_response_fit.json` 之外，不要求额外输出文件。
