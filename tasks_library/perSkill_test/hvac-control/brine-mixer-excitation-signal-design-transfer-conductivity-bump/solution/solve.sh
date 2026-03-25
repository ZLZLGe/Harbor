#!/bin/bash
set -euo pipefail

cd /root

python3 <<'PY'
import json
import statistics

from brine_mixer_simulator import BrineMixerSimulator


def moving_average(values, radius=1):
    smoothed = []
    for index in range(len(values)):
        start = max(0, index - radius)
        stop = min(len(values), index + radius + 1)
        window = values[start:stop]
        smoothed.append(sum(window) / len(window))
    return smoothed


simulator = BrineMixerSimulator("/root/mixing_station_profile.json")
profile = simulator.get_visible_profile()

step_pump_lpm = 3.4
baseline_steps = 9
hold_steps = 95

trace = [simulator.reset()]

for _ in range(baseline_steps):
    sample = simulator.step(0.0)
    trace.append(
        {
            "time_s": sample["time_s"],
            "conductivity_ms_cm": sample["conductivity_ms_cm"],
            "brine_pump_lpm": sample["brine_pump_lpm"],
        }
    )

for _ in range(hold_steps):
    sample = simulator.step(step_pump_lpm)
    trace.append(
        {
            "time_s": sample["time_s"],
            "conductivity_ms_cm": sample["conductivity_ms_cm"],
            "brine_pump_lpm": sample["brine_pump_lpm"],
        }
    )

step_start_index = next(
    index for index, sample in enumerate(trace) if sample["brine_pump_lpm"] > 0.0
)
baseline_samples = trace[:step_start_index]
step_samples = trace[step_start_index:]

baseline_mean = statistics.mean(
    sample["conductivity_ms_cm"] for sample in baseline_samples
)
tail_mean = statistics.mean(sample["conductivity_ms_cm"] for sample in trace[-12:])
observed_change = tail_mean - baseline_mean

smoothed = moving_average(
    [sample["conductivity_ms_cm"] for sample in step_samples],
    radius=1,
)
threshold = baseline_mean + 0.632 * observed_change
tau_index = next(
    index for index, value in enumerate(smoothed) if value >= threshold
)
time_constant_s = step_samples[tau_index]["time_s"] - step_samples[0]["time_s"]

gain_ms_cm_per_lpm = observed_change / step_pump_lpm
predicted_plateau_ms_cm = baseline_mean + gain_ms_cm_per_lpm * step_pump_lpm
remaining_gap_ms_cm = max(0.0, predicted_plateau_ms_cm - tail_mean)
near_steady_state = (
    remaining_gap_ms_cm <= 0.25
    and remaining_gap_ms_cm <= 0.12 * observed_change
)

evidence = (
    f"本次实验先记录了 {step_samples[0]['time_s']:.0f} 秒零流量基线，"
    f"再保持 {step_pump_lpm:.1f} L/min 阶跃直到 {trace[-1]['time_s']:.0f} 秒。"
    f" 最后 12 个样本均值比基线抬升 {observed_change:.2f} mS/cm，"
    f" 估计时间常数约 {time_constant_s:.1f} 秒，末段与预测平台值的剩余差距约"
    f" {remaining_gap_ms_cm:.3f} mS/cm，因此判断"
    f" {'已经' if near_steady_state else '尚未'}接近稳态。"
)

payload = {
    "experiment": {
        "baseline_pump_lpm": 0.0,
        "step_pump_lpm": step_pump_lpm,
        "baseline_duration_s": float(step_samples[0]["time_s"]),
        "hold_duration_s": float(step_samples[-1]["time_s"] - step_samples[0]["time_s"]),
        "sample_period_s": profile["sample_period_s"],
    },
    "trace": trace,
    "response_summary": {
        "baseline_mean_ms_cm": round(baseline_mean, 4),
        "tail_mean_ms_cm": round(tail_mean, 4),
        "observed_change_ms_cm": round(observed_change, 4),
    },
    "identified_model": {
        "model_type": "first_order_mixing_step",
        "gain_ms_cm_per_lpm": round(gain_ms_cm_per_lpm, 5),
        "time_constant_s": round(time_constant_s, 3),
        "predicted_plateau_ms_cm": round(predicted_plateau_ms_cm, 4),
    },
    "steady_state_assessment": {
        "near_steady_state": near_steady_state,
        "remaining_gap_ms_cm": round(remaining_gap_ms_cm, 4),
        "evidence": evidence,
    },
}

with open("/root/conductivity_bump_report.json", "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
PY
