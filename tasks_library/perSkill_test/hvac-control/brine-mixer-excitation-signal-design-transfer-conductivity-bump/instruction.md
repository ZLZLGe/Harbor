你在给一套盐水混合槽做开环摸底。目标不是闭环控制，而是设计一次单次投料泵阶跃实验，让槽内电导率响应既明显高于噪声，又不会冲到工艺浓度上限，并据此给出一份可用于后续建模的实验报告。

可用输入资产：
- `/root/brine_mixer_simulator.py`：盐水混合槽模拟器。
- `/root/mixing_station_profile.json`：可见的采样周期、噪声水平、建议阶跃窗口和安全上限。

请在 `/root/conductivity_bump_report.json` 写出一个 JSON 对象，至少包含这些字段：

```json
{
  "experiment": {
    "baseline_pump_lpm": 0.0,
    "step_pump_lpm": 3.4,
    "baseline_duration_s": 20.0,
    "hold_duration_s": 188.0,
    "sample_period_s": 2.0
  },
  "trace": [
    {
      "time_s": 0.0,
      "conductivity_ms_cm": 1.15,
      "brine_pump_lpm": 0.0
    }
  ],
  "response_summary": {
    "baseline_mean_ms_cm": 1.14,
    "tail_mean_ms_cm": 4.36,
    "observed_change_ms_cm": 3.22
  },
  "identified_model": {
    "model_type": "first_order_mixing_step",
    "gain_ms_cm_per_lpm": 0.95,
    "time_constant_s": 44.0,
    "predicted_plateau_ms_cm": 4.37
  },
  "steady_state_assessment": {
    "near_steady_state": true,
    "remaining_gap_ms_cm": 0.01,
    "evidence": "说明为什么这次保持时间已经足够长，或者为什么还没有足够接近稳态。"
  }
}
```

输出契约：
- 只需要提交这一个 JSON 文件。
- `trace` 必须来自同一次连续实验：先保持 `0.0 L/min` 基线，再切换到一次固定正向投料泵阶跃，并保持到实验结束；不允许多次切换、扫描或脉冲串。
- `trace` 的首个时间戳必须是 `0`，时间严格递增，总样本数不少于 `95`。
- `experiment.step_pump_lpm` 必须落在 `/root/mixing_station_profile.json` 的 `recommended_step_window_lpm` 区间内。
- `experiment.baseline_duration_s` 必须至少等于 `/root/mixing_station_profile.json` 的 `minimum_baseline_s`。
- `experiment.hold_duration_s` 必须至少等于 `/root/mixing_station_profile.json` 的 `minimum_hold_s`。
- `experiment.sample_period_s` 必须与 `/root/mixing_station_profile.json` 的 `sample_period_s` 一致，并与 `trace` 中的实际采样间隔一致。
- `response_summary.baseline_mean_ms_cm` 必须是全部基线样本的平均电导率；`tail_mean_ms_cm` 必须是最后 `12` 个样本的平均电导率；`observed_change_ms_cm` 必须等于两者之差。
- 为了证明激励明显高于噪声，`observed_change_ms_cm` 必须至少达到 `1.8`，并且至少是 `/root/mixing_station_profile.json` 中 `noise_std_ms_cm` 的 `8` 倍。
- 整条 `trace` 中的最大电导率必须严格低于 `/root/mixing_station_profile.json` 中的 `max_safe_conductivity_ms_cm`。
- `identified_model.model_type` 必须写成 `first_order_mixing_step`。
- `identified_model.gain_ms_cm_per_lpm`、`identified_model.time_constant_s` 和 `identified_model.predicted_plateau_ms_cm` 都必须是正数。
- `identified_model.predicted_plateau_ms_cm` 必须与 `response_summary.baseline_mean_ms_cm + identified_model.gain_ms_cm_per_lpm * experiment.step_pump_lpm` 一致，允许误差不超过 `0.1`。
- 评测会核对你估计的混合增益和时间常数：增益误差不超过 `12%`，时间常数误差不超过 `15%`。
- `steady_state_assessment.remaining_gap_ms_cm` 表示 `predicted_plateau_ms_cm - tail_mean_ms_cm`，如果这个差值因为噪声出现负数，可以写成 `0`。
- `steady_state_assessment.near_steady_state` 必须如实反映是否已经接近稳态：只有当 `remaining_gap_ms_cm <= 0.25` 且 `remaining_gap_ms_cm <= 0.12 * observed_change_ms_cm` 时才能写 `true`。
- `steady_state_assessment.evidence` 需要是一段至少 `35` 个字符的自然语言说明，明确解释你为什么判断已经接近稳态，或者为什么判断还不够接近稳态。

约束：
- 不要修改 `/root/brine_mixer_simulator.py` 或 `/root/mixing_station_profile.json`。
- 输出必须是合法 JSON，且顶层字段名与上面的契约一致；可以增加额外字段，但不要省略必需字段。
