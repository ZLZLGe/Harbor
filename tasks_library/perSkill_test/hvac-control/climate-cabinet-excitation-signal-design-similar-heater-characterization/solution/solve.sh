#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import statistics

from cabinet_simulator import ClimateCabinetSimulator


def to_sample(state):
    return {
        "time_s": round(float(state["time_s"]), 3),
        "temperature_c": round(float(state["temperature_c"]), 4),
        "heater_percent": round(float(state["heater_percent"]), 3),
    }


def moving_average(values, radius=1):
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - radius)
        stop = min(len(values), index + radius + 1)
        window = values[start:stop]
        smoothed.append(sum(window) / len(window))
    return smoothed


simulator = ClimateCabinetSimulator("/root/cabinet_profile.json")
profile = simulator.get_visible_profile()

baseline_duration_s = 30.0
step_duration_s = 500.0
step_heater_percent = 45.0
sample_period_s = profile["sample_period_s"]

response_segment = []
initial = simulator.reset()
response_segment.append(to_sample(initial))

for _ in range(int(baseline_duration_s / sample_period_s)):
    response_segment.append(to_sample(simulator.step(0.0)))

for _ in range(int(step_duration_s / sample_period_s)):
    response_segment.append(to_sample(simulator.step(step_heater_percent)))

step_start_index = next(
    index for index, sample in enumerate(response_segment) if sample["heater_percent"] > 0.0
)
baseline_temps = [sample["temperature_c"] for sample in response_segment[:step_start_index]]
step_samples = response_segment[step_start_index:]
step_temps = [sample["temperature_c"] for sample in step_samples]

baseline_average = statistics.mean(baseline_temps)
tail_average = statistics.mean(step_temps[-8:])
observed_rise_c = tail_average - baseline_average
gain_c_per_percent = observed_rise_c / step_heater_percent

threshold = baseline_average + 0.632 * observed_rise_c
smoothed_step_temps = moving_average(step_temps, radius=1)
threshold_index = next(
    index for index, value in enumerate(smoothed_step_temps) if value >= threshold
)
time_constant_s = step_samples[threshold_index]["time_s"] - step_samples[0]["time_s"]

sample_times = [sample["time_s"] for sample in response_segment]
intervals = [
    sample_times[index + 1] - sample_times[index]
    for index in range(len(sample_times) - 1)
]
tail_slopes = []
for earlier, later in zip(step_samples[-6:-1], step_samples[-5:]):
    delta_t = later["time_s"] - earlier["time_s"]
    tail_slopes.append(abs((later["temperature_c"] - earlier["temperature_c"]) / delta_t))

sufficiency_reason = (
    f"本次实验先在 0% 加热下记录了 {baseline_duration_s:.0f} 秒基线，再施加 "
    f"{step_heater_percent:.0f}% 固定阶跃并保持 {step_duration_s:.0f} 秒。"
    f" 共采集 {len(response_segment)} 个样本，采样周期 {sample_period_s:.1f} 秒，"
    f" 相当于每个时间常数大约覆盖 {time_constant_s / sample_period_s:.1f} 个采样点。"
    f" 阶跃后末段均值相对基线抬升约 {observed_rise_c:.2f} 摄氏度，"
    f" 末段平均绝对斜率约 {statistics.mean(tail_slopes):.4f} 摄氏度每秒，"
    f" 说明响应已经明显接近平衡，足以支撑后续整定。"
)

payload = {
    "experiment": {
        "baseline_heater_percent": 0.0,
        "step_heater_percent": step_heater_percent,
        "baseline_duration_s": float(step_samples[0]["time_s"]),
        "step_duration_s": float(step_samples[-1]["time_s"] - step_samples[0]["time_s"]),
        "sample_period_s": float(round(statistics.mean(intervals), 3)),
    },
    "response_segment": response_segment,
    "identified_model": {
        "model_type": "first_order_heating_step",
        "gain_c_per_percent": round(gain_c_per_percent, 5),
        "time_constant_s": round(time_constant_s, 3),
    },
    "sufficiency_reason": sufficiency_reason,
    "diagnostics": {
        "baseline_average_c": round(baseline_average, 4),
        "tail_average_c": round(tail_average, 4),
        "observed_rise_c": round(observed_rise_c, 4),
        "tail_mean_abs_slope_c_per_s": round(statistics.mean(tail_slopes), 6),
    },
}

with open("/root/chamber_characterization.json", "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
PY
