你要为一台传送带电机测试台做一次开环速度辨识。设备接下来要接上真实输送带，所以现在只允许做一次空载 PWM 阶跃试验；机械组只会接收你输出的辨识结果，不会替你补采数据。

可用环境：
- `motor_bench.py`：电机与转速计仿真器
- `motor_bench_config.json`：测试台可见约束，包括采样周期、转速安全上限和当前初始状态

请自行设计并执行一次既安全、又足以看清速度动态的单次 PWM 阶跃试验，并在 `/root/motor_speed_model.json` 输出结果。要求：

1. 试验必须从 0% PWM 的静止状态开始，先保留一小段基线数据，再切换到一个固定正 PWM，占空比保持到试验结束。
2. 全程转速必须严格低于配置中的安全上限，不能触发超速停机。
3. 采样间隔必须固定，原始日志要能清楚反映电机速度从静止爬升到接近稳态的过程。
4. 基于这次试验数据拟合一个一阶速度模型，给出稳态增益和时间常数。

`motor_speed_model.json` 至少需要包含以下字段：

```json
{
  "excitation_plan": {
    "baseline_duration_sec": 0.3,
    "pwm_step_percent": 36.0,
    "sample_interval_sec": 0.02,
    "total_duration_sec": 2.7
  },
  "speed_response": [
    {
      "time_s": 0.0,
      "speed_rpm": 3.2,
      "pwm_percent": 0.0
    }
  ],
  "identified_dynamics": {
    "steady_gain_rpm_per_percent": 34.8,
    "time_constant_sec": 0.42,
    "fit_rmse_rpm": 6.5
  }
}
```

补充要求：
- `speed_response` 中每条记录都要包含 `time_s`、`speed_rpm`、`pwm_percent`。
- `excitation_plan.total_duration_sec` 必须和原始日志的总时长一致。
- `excitation_plan.pwm_step_percent` 必须和阶跃后的恒定 PWM 一致。
- `identified_dynamics.fit_rmse_rpm` 填写你的拟合误差。

除了 `motor_speed_model.json` 之外，不要求额外输出文件。
