你在调试一台用于器件老化预试验的小型恒温柜。现在不需要做闭环控制，只需要设计并执行一次高质量的开环加热阶跃实验，用它来刻画这个柜体的热惯性。

可用输入资产：
- `/root/cabinet_simulator.py`：恒温柜模拟器。
- `/root/cabinet_profile.json`：可见的运行约束、采样周期、噪声水平和安全温度上限。

要求在 `/root/chamber_characterization.json` 中写出一个 JSON 对象，至少包含这些字段：

```json
{
  "experiment": {
    "baseline_heater_percent": 0.0,
    "step_heater_percent": 45.0,
    "baseline_duration_s": 30.0,
    "step_duration_s": 500.0,
    "sample_period_s": 5.0
  },
  "response_segment": [
    {
      "time_s": 0.0,
      "temperature_c": 19.5,
      "heater_percent": 0.0
    }
  ],
  "identified_model": {
    "model_type": "first_order_heating_step",
    "gain_c_per_percent": 0.11,
    "time_constant_s": 150.0
  },
  "sufficiency_reason": "说明为什么这次阶跃在安全范围内、为什么数据量和采样覆盖已经足够继续做后续整定。"
}
```

输出契约：
- 只需要提交这一个文件，不要提交闭环控制日志。
- `response_segment` 必须来自同一次连续实验，先保持 `0%` 加热，再切换到一次固定的正向加热阶跃并保持到结束。
- `response_segment` 的首个时间戳必须是 `0`，时间严格递增，总样本数不少于 `80`。
- `experiment.step_heater_percent` 必须在 `20` 到 `60` 之间。
- `experiment.baseline_duration_s` 必须至少 `30` 秒。
- `experiment.step_duration_s` 必须至少 `360` 秒。
- `experiment.sample_period_s` 必须不大于 `6` 秒，并与 `response_segment` 中的实际采样间隔一致。
- 为了证明这次激励足够有信息量，阶跃后末段平均温度相对阶跃前基线平均温度的提升必须至少 `3.0` 摄氏度。
- `identified_model.gain_c_per_percent` 和 `identified_model.time_constant_s` 都必须是正数，并且需要足够接近模拟器真实系统：增益误差不超过 `15%`，时间常数误差不超过 `20%`。
- `sufficiency_reason` 写成一段自然语言说明，至少 `40` 个字符，明确回答“为什么这组数据已经足够支撑后续整定”。

约束：
- 不要修改 `/root/cabinet_simulator.py` 或 `/root/cabinet_profile.json`。
- 加热实验必须保持在安全范围内，不能让系统持续冲到安全切断。
- 输出必须是合法 JSON，且顶层字段名与上面的契约一致；可以增加额外字段，但不要省略必需字段。
