#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import csv
import math
import textwrap
import yaml

root = Path("/root")

pid_controller_code = textwrap.dedent(
    '''
    """Discrete PID controller used by the hill descent governor."""


    class PIDController:
        def __init__(self, kp, ki, kd, output_limits=None, integral_limit=None):
            self.kp = float(kp)
            self.ki = float(ki)
            self.kd = float(kd)
            self.output_limits = output_limits
            self.integral_limit = integral_limit
            self.reset()

        def reset(self):
            self.integral = 0.0
            self.prev_error = None

        def compute(self, error, dt):
            if dt <= 0:
                return 0.0

            self.integral += error * dt
            if self.integral_limit is not None:
                limit = abs(float(self.integral_limit))
                self.integral = max(-limit, min(limit, self.integral))

            derivative = 0.0
            if self.prev_error is not None:
                derivative = (error - self.prev_error) / dt
            self.prev_error = error

            output = self.kp * error + self.ki * self.integral + self.kd * derivative
            if self.output_limits is not None:
                lo, hi = self.output_limits
                if lo is not None:
                    output = max(lo, output)
                if hi is not None:
                    output = min(hi, output)
            return float(output)
    '''
).strip() + "\n"

hill_descent_governor_code = textwrap.dedent(
    '''
    """Grade-aware hill descent governor with feedforward brake blending."""

    import math

    from pid_controller import PIDController


    class HillDescentGovernor:
        def __init__(self, config):
            vehicle = config["vehicle"]
            controller = config["controller"]
            pid_cfg = config.get("pid_brake_tuned", config["pid_brake"])

            self.mass = float(vehicle["mass_kg"])
            self.drag_area = float(vehicle["drag_area_m2"])
            self.rolling_resistance = float(vehicle["rolling_resistance"])
            self.air_density = float(vehicle["air_density_kgpm3"])
            self.gravity = float(vehicle["gravity_mps2"])
            self.max_brake = float(vehicle["max_service_brake_decel_mps2"])
            self.integral_limit = float(controller["integral_limit"])

            self.pid = PIDController(
                pid_cfg["kp"],
                pid_cfg["ki"],
                pid_cfg["kd"],
                output_limits=(0.0, self.max_brake),
                integral_limit=self.integral_limit,
            )

        def components(self, vehicle_speed, grade_percent):
            theta = math.atan(float(grade_percent) / 100.0)
            gravity_accel = self.gravity * math.sin(theta)
            drag_accel = 0.5 * self.air_density * self.drag_area * float(vehicle_speed) ** 2 / self.mass
            rolling_accel = self.rolling_resistance * self.gravity * math.cos(theta)
            return gravity_accel, drag_accel, rolling_accel

        def compute(self, vehicle_speed, target_speed, grade_percent, dt):
            gravity_accel, drag_accel, rolling_accel = self.components(vehicle_speed, grade_percent)
            feedforward = max(0.0, gravity_accel - drag_accel - rolling_accel)
            speed_error = float(vehicle_speed) - float(target_speed)
            corrective = max(0.0, self.pid.compute(speed_error, dt))
            brake_decel = min(self.max_brake, max(0.0, feedforward + corrective))
            brake_command = brake_decel / self.max_brake if self.max_brake else 0.0
            return float(brake_command), float(brake_decel), float(speed_error)
    '''
).strip() + "\n"

descent_simulation_code = textwrap.dedent(
    '''
    """Run the grade-aware hill descent simulation and export metrics."""

    from __future__ import annotations

    import csv
    from pathlib import Path

    import yaml

    from hill_descent_governor import HillDescentGovernor


    ROOT = Path("/root")
    STEADY_WINDOWS = [(0.0, 37.0), (53.0, 67.0), (83.0, 92.0), (108.0, 142.0), (158.0, 180.0)]
    SETTLING_KEYS = {
        "after_target_drop_45s": 45.0,
        "after_grade_step_75s": 75.0,
        "after_target_drop_100s": 100.0,
        "after_target_change_150s": 150.0,
    }


    def load_csv(path):
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [
                {key: float(value) for key, value in row.items()}
                for row in csv.DictReader(handle)
            ]


    def in_windows(time_value, windows):
        return any(start <= time_value <= end for start, end in windows)


    def settling_time(rows, change_time, band, samples):
        start_index = next(index for index, row in enumerate(rows) if row["time"] == change_time)
        for index in range(start_index, len(rows) - samples + 1):
            if all(abs(rows[offset]["speed_error"]) <= band for offset in range(index, index + samples)):
                return float(rows[index]["time"] - change_time)
        return None


    def run():
        with (ROOT / "descent_vehicle.yaml").open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        with (ROOT / "descent_tuning.yaml").open("r", encoding="utf-8") as handle:
            tuning = yaml.safe_load(handle)

        config["pid_brake_tuned"] = tuning["pid_brake"]
        governor = HillDescentGovernor(config)

        grade_rows = load_csv(ROOT / "grade_profile.csv")
        target_rows = load_csv(ROOT / "target_speed_profile.csv")
        if len(grade_rows) != len(target_rows):
            raise ValueError("CSV profiles must have the same number of rows")

        dt = float(config["simulation"]["dt"])
        vehicle_speed = float(config["controller"]["initial_speed_mps"])
        results = []

        for grade_row, target_row in zip(grade_rows, target_rows):
            if abs(grade_row["time"] - target_row["time"]) > 1e-9:
                raise ValueError("Profile timestamps must align")

            time_value = float(grade_row["time"])
            grade_percent = float(grade_row["grade_percent"])
            target_speed = float(target_row["target_speed"])

            brake_command, brake_decel, speed_error = governor.compute(
                vehicle_speed, target_speed, grade_percent, dt
            )
            gravity_accel, drag_accel, rolling_accel = governor.components(vehicle_speed, grade_percent)
            net_accel = gravity_accel - drag_accel - rolling_accel - brake_decel

            results.append(
                {
                    "time": round(time_value, 1),
                    "grade_percent": grade_percent,
                    "target_speed": target_speed,
                    "vehicle_speed": vehicle_speed,
                    "speed_error": speed_error,
                    "brake_command": brake_command,
                    "brake_decel": brake_decel,
                    "gravity_accel": gravity_accel,
                    "drag_accel": drag_accel,
                    "rolling_accel": rolling_accel,
                    "net_accel": net_accel,
                }
            )

            vehicle_speed = max(0.0, vehicle_speed + net_accel * dt)

        with (ROOT / "descent_simulation_results.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "time",
                    "grade_percent",
                    "target_speed",
                    "vehicle_speed",
                    "speed_error",
                    "brake_command",
                    "brake_decel",
                    "gravity_accel",
                    "drag_accel",
                    "rolling_accel",
                    "net_accel",
                ],
            )
            writer.writeheader()
            writer.writerows(results)

        steady_rows = [row for row in results if in_windows(row["time"], STEADY_WINDOWS)]
        metrics = {
            "max_transient_overspeed_mps": float(max(row["speed_error"] for row in results)),
            "steady_max_overspeed_mps": float(max(row["speed_error"] for row in steady_rows)),
            "steady_mean_abs_error_mps": float(
                sum(abs(row["speed_error"]) for row in steady_rows) / len(steady_rows)
            ),
            "settling_times_s": {},
            "safety": {
                "max_vehicle_speed_mps": float(max(row["vehicle_speed"] for row in results)),
                "max_brake_decel_mps2": float(max(row["brake_decel"] for row in results)),
                "within_service_brake_limit": bool(
                    max(row["brake_decel"] for row in results)
                    <= float(config["vehicle"]["max_service_brake_decel_mps2"]) + 1e-9
                ),
            },
        }

        band = float(config["controller"]["settling_error_band_mps"])
        samples = int(config["controller"]["settling_samples"])
        for key, change_time in SETTLING_KEYS.items():
            value = settling_time(results, change_time, band, samples)
            metrics["settling_times_s"][key] = float(value) if value is not None else None

        with (ROOT / "descent_metrics.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(metrics, handle, sort_keys=False)


    if __name__ == "__main__":
        run()
    '''
).strip() + "\n"

tuning = {
    "pid_brake": {
        "kp": 1.3,
        "ki": 0.12,
        "kd": 0.18,
    }
}

(root / "pid_controller.py").write_text(pid_controller_code, encoding="utf-8")
(root / "hill_descent_governor.py").write_text(hill_descent_governor_code, encoding="utf-8")
(root / "descent_simulation.py").write_text(descent_simulation_code, encoding="utf-8")
with (root / "descent_tuning.yaml").open("w", encoding="utf-8") as handle:
    yaml.safe_dump(tuning, handle, sort_keys=False)

with (root / "descent_simulation.py").open("r", encoding="utf-8"):
    pass
PY

python3 /root/descent_simulation.py
