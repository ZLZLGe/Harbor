#!/bin/bash
set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
export TASK_ROOT

python3 <<'PY'
from pathlib import Path
import os
import subprocess

root = Path(os.environ["TASK_ROOT"])

pid_controller_code = '''"""Discrete-time PID controller for liquid level tasks."""


class PIDController:
    def __init__(self, kp, ki, kd, output_min=None, output_max=None, integral_limit=None):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.output_min = output_min
        self.output_max = output_max
        self.integral_limit = integral_limit
        self.integral = 0.0
        self.prev_error = None

    def reset(self):
        self.integral = 0.0
        self.prev_error = None

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0

        self.integral += error * dt
        if self.integral_limit is not None:
            self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))

        derivative = 0.0 if self.prev_error is None else (error - self.prev_error) / dt
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error

        if self.output_min is not None:
            output = max(self.output_min, output)
        if self.output_max is not None:
            output = min(self.output_max, output)
        return float(output)
'''

tank_controller_code = '''"""Tank level controller built on a PID loop."""

import math

from pid_controller import PIDController


class TankLevelController:
    def __init__(self, config):
        self.config = config
        tank = config["tank"]
        pump = config["pump"]
        simulation = config["simulation"]
        pid = config["pid"]

        self.target_level_m = float(tank["target_level_m"])
        self.nominal_inflow_lps = float(simulation["nominal_inflow_lps"])
        self.feedforward_gain = float(simulation.get("inflow_feedforward_gain", 0.0))
        self.nominal_pump_lps = self.nominal_inflow_lps - float(
            tank["outlet_coeff_lps_per_sqrt_m"]
        ) * math.sqrt(self.target_level_m)
        self.min_pump_lps = float(pump["min_pump_lps"])
        self.max_pump_lps = float(pump["max_pump_lps"])

        self.pid = PIDController(
            kp=pid["kp"],
            ki=pid["ki"],
            kd=pid["kd"],
            output_min=-self.max_pump_lps,
            output_max=self.max_pump_lps,
            integral_limit=float(simulation["integral_limit"]),
        )

    def compute(self, target_level_m, actual_level_m, inflow_lps, dt):
        level_error_m = float(target_level_m) - float(actual_level_m)
        correction = self.pid.compute(level_error_m, dt)
        requested_pump_lps = (
            self.nominal_pump_lps
            + self.feedforward_gain * (float(inflow_lps) - self.nominal_inflow_lps)
            - correction
        )
        requested_pump_lps = max(
            self.min_pump_lps, min(self.max_pump_lps, requested_pump_lps)
        )
        return float(requested_pump_lps), float(level_error_m)
'''

simulate_tank_code = '''"""Run the liquid level closed-loop simulation."""

import math
from pathlib import Path

import pandas as pd
import yaml

from tank_controller import TankLevelController


def clip(value, low, high):
    return max(low, min(high, value))


def resolve_input(task_root, filename):
    direct = task_root / filename
    if direct.exists():
        return direct
    fallback = task_root / "environment" / filename
    return fallback


def compute_metrics(trace):
    initial = trace[(trace["time_s"] >= 15.0) & (trace["time_s"] <= 25.0)]
    surge = trace[(trace["time_s"] >= 54.0) & (trace["time_s"] <= 66.0)]
    final = trace[(trace["time_s"] >= 100.0) & (trace["time_s"] <= 120.0)]
    return {
        "initial_recovery_mae": float(initial["level_error_m"].abs().mean()),
        "surge_recovery_mae": float(surge["level_error_m"].abs().mean()),
        "final_window_mae": float(final["level_error_m"].abs().mean()),
        "peak_level_m": float(trace["actual_level_m"].max()),
    }


def run_simulation(task_root):
    task_root = Path(task_root)
    with open(resolve_input(task_root, "tank_config.yaml"), "r", encoding="utf-8") as f:
        base_config = yaml.safe_load(f)
    with open(task_root / "tank_tuning.yaml", "r", encoding="utf-8") as f:
        tuning = yaml.safe_load(f)

    config = {
        "tank": base_config["tank"],
        "pump": base_config["pump"],
        "simulation": base_config["simulation"],
        "pid": tuning["pid"],
    }

    tank = config["tank"]
    pump = config["pump"]
    simulation = config["simulation"]

    controller = TankLevelController(config)
    inflow_profile = pd.read_csv(resolve_input(task_root, "inflow_profile.csv"))

    dt = float(simulation["dt"])
    level_m = float(tank["initial_level_m"])
    actual_pump_lps = float(pump["initial_pump_lps"])
    rows = []

    for record in inflow_profile.itertuples(index=False):
        time_s = float(record.time_s)
        inflow_lps = float(record.inflow_lps)
        requested_pump_lps, level_error_m = controller.compute(
            target_level_m=tank["target_level_m"],
            actual_level_m=level_m,
            inflow_lps=inflow_lps,
            dt=dt,
        )

        max_step = float(pump["pump_ramp_limit_lps_per_s"]) * dt
        pump_delta = clip(requested_pump_lps - actual_pump_lps, -max_step, max_step)
        actual_pump_lps = clip(
            actual_pump_lps + pump_delta,
            float(pump["min_pump_lps"]),
            float(pump["max_pump_lps"]),
        )

        rows.append(
            {
                "time_s": time_s,
                "target_level_m": float(tank["target_level_m"]),
                "actual_level_m": level_m,
                "inflow_lps": inflow_lps,
                "requested_pump_lps": requested_pump_lps,
                "actual_pump_lps": actual_pump_lps,
                "level_error_m": level_error_m,
            }
        )

        gravity_outflow_lps = float(tank["outlet_coeff_lps_per_sqrt_m"]) * math.sqrt(
            max(level_m, 0.0)
        )
        total_outflow_lps = actual_pump_lps + gravity_outflow_lps
        level_m = clip(
            level_m + ((inflow_lps - total_outflow_lps) / float(tank["tank_area_m2"])) * dt,
            float(tank["min_level_m"]),
            float(tank["max_level_m"]),
        )

    trace = pd.DataFrame(rows)
    trace.to_csv(task_root / "tank_level_response.csv", index=False)
    return trace


def main():
    task_root = Path(__file__).resolve().parent
    run_simulation(task_root)


if __name__ == "__main__":
    main()
'''

tuning_seed = '''pid:
  kp: 4.2
  ki: 0.12
  kd: 0.1
metrics:
  initial_recovery_mae: 0.0
  surge_recovery_mae: 0.0
  final_window_mae: 0.0
  peak_level_m: 0.0
'''

report_text = '''# 储液罐液位控制报告

## 液位平衡模型与控制器设计

液位模型由进流、泵抽排和重力泄流组成。控制器使用离散 PID 计算泵的请求流量，再经过泵速率限制形成实际泵流量，从而反映执行器不能瞬时跳变的过程约束。

## 参数调节过程与最终参数

调参时先确定名义工况下的基准泵流量，再逐步提高比例项以缩短初始恢复时间，最后加入少量积分与微分项来减小大扰动后的尾差与泵流量波动。最终参数为 kp=4.2、ki=0.12、kd=0.10。

## 进流量扰动、泵速率限制和末段稳定性结果

在 15s 到 25s 的初始恢复窗口内，液位误差已经收敛到较小范围。52s 之后的大流量扰动阶段，泵因为速率限制不能立即跟随，但仍能在要求窗口内恢复。100s 到 120s 的末段平衡窗口保持了较低平均误差，峰值液位也没有超过限制。
'''

(root / "pid_controller.py").write_text(pid_controller_code, encoding="utf-8")
(root / "tank_controller.py").write_text(tank_controller_code, encoding="utf-8")
(root / "simulate_tank.py").write_text(simulate_tank_code, encoding="utf-8")
(root / "tank_tuning.yaml").write_text(tuning_seed, encoding="utf-8")
(root / "level_control_report.md").write_text(report_text, encoding="utf-8")

subprocess.run(["python3", str(root / "simulate_tank.py")], check=True)

import pandas as pd
import yaml

trace = pd.read_csv(root / "tank_level_response.csv")
initial = trace[(trace["time_s"] >= 15.0) & (trace["time_s"] <= 25.0)]["level_error_m"].abs().mean()
surge = trace[(trace["time_s"] >= 54.0) & (trace["time_s"] <= 66.0)]["level_error_m"].abs().mean()
final = trace[(trace["time_s"] >= 100.0) & (trace["time_s"] <= 120.0)]["level_error_m"].abs().mean()
peak = trace["actual_level_m"].max()

tuning = {
    "pid": {"kp": 4.2, "ki": 0.12, "kd": 0.1},
    "metrics": {
        "initial_recovery_mae": round(float(initial), 6),
        "surge_recovery_mae": round(float(surge), 6),
        "final_window_mae": round(float(final), 6),
        "peak_level_m": round(float(peak), 6),
    },
}

with open(root / "tank_tuning.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(tuning, f, sort_keys=False, allow_unicode=True)
PY
