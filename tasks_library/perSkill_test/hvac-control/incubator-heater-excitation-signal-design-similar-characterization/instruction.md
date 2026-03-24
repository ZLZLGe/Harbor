你接手的是一台台式恒温培养箱的加热辨识工作。设备刚完成维护，当前只能做一次开环加热试验来摸清热惯性，之后别的同事会拿你的结果继续整定控制器。

可用环境：
- `incubator_simulator.py`：培养箱热模型仿真器
- `incubator_profile.json`：可见运行参数，包括采样周期、当前稳定温度和安全上限

请设计并执行一次安全、信息量足够的单次加热阶跃试验，并在 `/root/incubator_identification_report.json` 输出结果。要求：

1. 试验必须从稳定的 0% 加热开始，先保留一小段基线数据，再切到一个固定正加热功率，并保持到试验结束。
2. 全程温度必须严格低于安全上限，不能触发危险过热。
3. 采样间隔必须固定，原始响应数据要足以看清一阶热惯性的上升过程。
4. 基于这次试验数据拟合一个一阶模型，给出加热增益和时间常数。

`incubator_identification_report.json` 必须至少包含以下字段：

```json
{
  "heater_step_percent": 30.0,
  "sample_interval_sec": 5.0,
  "step_start_time_sec": 20.0,
  "test_duration_sec": 420.0,
  "safety_limit_c": 38.4,
  "raw_response": [
    {
      "time_s": 0.0,
      "temperature_c": 34.6,
      "heater_percent": 0.0
    }
  ],
  "identified_model": {
    "gain_c_per_percent": 0.095,
    "time_constant_sec": 95.0,
    "fit_rmse_c": 0.08
  }
}
```

补充要求：
- `raw_response` 中每条记录都要包含 `time_s`、`temperature_c`、`heater_percent`。
- `test_duration_sec` 要和原始数据时长一致。
- `heater_step_percent` 要和阶跃后的恒定功率一致。
- `identified_model.fit_rmse_c` 填写你的拟合误差。

除了 `incubator_identification_report.json` 之外，不要求额外输出文件。
