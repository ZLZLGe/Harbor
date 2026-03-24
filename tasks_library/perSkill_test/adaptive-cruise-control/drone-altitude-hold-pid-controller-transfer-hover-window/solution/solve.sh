#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path
import textwrap
import pandas as pd
import yaml

ROOT = Path.cwd()

pid_controller_code = textwrap.dedent(
    '''
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
).strip() + "\n"

altitude_controller_code = textwrap.dedent(
    '''
    import yaml

    from pid_controller import PIDController


    class AltitudeHoldController:
        def __init__(self, config):
            drone = config["drone"]
            pid_cfg = config["pid"]
            limit = config["simulation"]["integral_limit"]
            self.controller = PIDController(
                kp=pid_cfg["kp"],
                ki=pid_cfg["ki"],
                kd=pid_cfg["kd"],
                output_min=drone["min_collective_accel_mps2"],
                output_max=drone["max_collective_accel_mps2"],
                integral_limit=limit,
            )

        def compute(self, target_altitude, actual_altitude, vertical_speed, dt):
            altitude_error = float(target_altitude - actual_altitude)
            collective_cmd = self.controller.compute(altitude_error, dt)
            return float(collective_cmd), altitude_error
    '''
).strip() + "\n"

simulate_code = textwrap.dedent(
    '''
    from pathlib import Path

    import pandas as pd
    import yaml

    from altitude_controller import AltitudeHoldController


    def build_target_series(mission_df, dt, duration):
        samples = []
        for idx in range(int(round(duration / dt)) + 1):
            t = round(idx * dt, 1)
            row = mission_df[
                (mission_df["start_time"] <= t + 1e-9)
                & ((mission_df["end_time"] > t + 1e-9) | (abs(mission_df["end_time"] - duration) < 1e-9))
            ].iloc[0]
            samples.append({"time": t, "target_altitude": float(row["target_altitude_m"])})
        return pd.DataFrame(samples)


    def build_gust_series(gust_df, dt, duration):
        values = []
        for idx in range(int(round(duration / dt)) + 1):
            t = round(idx * dt, 1)
            active = gust_df[
                (gust_df["start_time"] <= t + 1e-9)
                & ((gust_df["end_time"] > t + 1e-9) | (abs(gust_df["end_time"] - duration) < 1e-9))
            ]
            gust_accel = float(active["gust_accel_mps2"].sum()) if len(active) else 0.0
            values.append({"time": t, "gust_accel": gust_accel})
        return pd.DataFrame(values)


    def run_simulation(root):
        root = Path(root)
        config = yaml.safe_load((root / "drone_config.yaml").read_text())
        tuning = yaml.safe_load((root / "altitude_tuning.yaml").read_text())
        mission_df = pd.read_csv(root / "mission_profile.csv")
        gust_df = pd.read_csv(root / "gust_windows.csv")

        runtime_config = {
            "drone": config["drone"],
            "simulation": config["simulation"],
            "pid": tuning["pid"],
        }
        controller = AltitudeHoldController(runtime_config)

        dt = float(config["simulation"]["dt"])
        duration = float(config["simulation"]["duration"])
        damping = float(config["drone"]["vertical_damping"])
        max_climb = float(config["drone"]["max_climb_rate_mps"])
        max_sink = float(config["drone"]["max_sink_rate_mps"])

        targets = build_target_series(mission_df, dt, duration)
        gusts = build_gust_series(gust_df, dt, duration)
        profile = targets.merge(gusts, on="time")

        altitude = float(config["drone"]["initial_altitude_m"])
        vertical_speed = float(config["drone"]["initial_vertical_speed_mps"])

        rows = []
        for sample in profile.itertuples(index=False):
            collective_cmd, altitude_error = controller.compute(
                sample.target_altitude, altitude, vertical_speed, dt
            )
            rows.append(
                {
                    "time": sample.time,
                    "target_altitude": sample.target_altitude,
                    "actual_altitude": altitude,
                    "vertical_speed": vertical_speed,
                    "collective_cmd": collective_cmd,
                    "gust_accel": sample.gust_accel,
                    "altitude_error": altitude_error,
                }
            )

            net_vertical_accel = collective_cmd + sample.gust_accel - damping * vertical_speed
            vertical_speed = max(max_sink, min(max_climb, vertical_speed + net_vertical_accel * dt))
            altitude = max(0.0, altitude + vertical_speed * dt)

        result = pd.DataFrame(rows)
        result.to_csv(root / "altitude_hold_trace.csv", index=False)
        return result


    if __name__ == "__main__":
        run_simulation(Path.cwd())
    '''
).strip() + "\n"

config = yaml.safe_load((ROOT / "drone_config.yaml").read_text())
mission_df = pd.read_csv(ROOT / "mission_profile.csv")
gust_df = pd.read_csv(ROOT / "gust_windows.csv")

def build_target_series(dt, duration):
    samples = []
    for idx in range(int(round(duration / dt)) + 1):
        t = round(idx * dt, 1)
        row = mission_df[
            (mission_df["start_time"] <= t + 1e-9)
            & ((mission_df["end_time"] > t + 1e-9) | (abs(mission_df["end_time"] - duration) < 1e-9))
        ].iloc[0]
        samples.append({"time": t, "target_altitude": float(row["target_altitude_m"])})
    return pd.DataFrame(samples)


def build_gust_series(dt, duration):
    samples = []
    for idx in range(int(round(duration / dt)) + 1):
        t = round(idx * dt, 1)
        active = gust_df[
            (gust_df["start_time"] <= t + 1e-9)
            & ((gust_df["end_time"] > t + 1e-9) | (abs(gust_df["end_time"] - duration) < 1e-9))
        ]
        gust_accel = float(active["gust_accel_mps2"].sum()) if len(active) else 0.0
        samples.append({"time": t, "gust_accel": gust_accel})
    return pd.DataFrame(samples)


def simulate(pid):
    dt = float(config["simulation"]["dt"])
    duration = float(config["simulation"]["duration"])
    damping = float(config["drone"]["vertical_damping"])
    max_climb = float(config["drone"]["max_climb_rate_mps"])
    max_sink = float(config["drone"]["max_sink_rate_mps"])
    integral_limit = float(config["simulation"]["integral_limit"])
    output_min = float(config["drone"]["min_collective_accel_mps2"])
    output_max = float(config["drone"]["max_collective_accel_mps2"])

    targets = build_target_series(dt, duration)
    gusts = build_gust_series(dt, duration)
    profile = targets.merge(gusts, on="time")

    altitude = float(config["drone"]["initial_altitude_m"])
    vertical_speed = float(config["drone"]["initial_vertical_speed_mps"])
    integral = 0.0
    prev_error = None
    rows = []

    for sample in profile.itertuples(index=False):
        error = float(sample.target_altitude - altitude)
        integral += error * dt
        integral = max(-integral_limit, min(integral_limit, integral))
        derivative = 0.0 if prev_error is None else (error - prev_error) / dt
        collective_cmd = pid["kp"] * error + pid["ki"] * integral + pid["kd"] * derivative
        collective_cmd = max(output_min, min(output_max, collective_cmd))

        rows.append(
            {
                "time": sample.time,
                "target_altitude": sample.target_altitude,
                "actual_altitude": altitude,
                "vertical_speed": vertical_speed,
                "collective_cmd": collective_cmd,
                "gust_accel": sample.gust_accel,
                "altitude_error": error,
            }
        )

        net_vertical_accel = collective_cmd + sample.gust_accel - damping * vertical_speed
        vertical_speed = max(max_sink, min(max_climb, vertical_speed + net_vertical_accel * dt))
        altitude = max(0.0, altitude + vertical_speed * dt)
        prev_error = error

    return pd.DataFrame(rows)


final_pid = {"kp": 2.2, "ki": 0.04, "kd": 0.6}
trace = simulate(final_pid)

post_gust_windows = [(10.0, 15.0), (37.0, 42.0), (55.0, 60.0), (82.0, 87.0)]
step_windows = [(21.0, 30.0), (66.0, 75.0)]

worst_post_gust = max(
    trace[(trace["time"] >= start) & (trace["time"] <= end)]["altitude_error"].abs().mean()
    for start, end in post_gust_windows
)
max_step_window = max(
    trace[(trace["time"] >= start) & (trace["time"] <= end)]["altitude_error"].abs().mean()
    for start, end in step_windows
)
final_hover = trace[(trace["time"] >= 84.0) & (trace["time"] <= 90.0)]["altitude_error"].abs().mean()

tuning = {
    "pid": final_pid,
    "metrics": {
        "worst_post_gust_mae": round(float(worst_post_gust), 4),
        "max_step_window_mae": round(float(max_step_window), 4),
        "final_hover_mae": round(float(final_hover), 4),
    },
}

report = textwrap.dedent(
    f'''
    # Hover Analysis

    ## Vertical Dynamics Design
    The simulation uses a single-axis vertical model with collective acceleration command, gust acceleration disturbance, and linear damping on vertical speed. The controller closes the loop on altitude error and respects the configured command and climb-rate limits.

    ## Tuning Process
    I started from the initial gains in `drone_config.yaml`, increased proportional gain to shorten altitude recovery after step changes, added derivative gain to reduce oscillation during gust exits, and used a small integral gain to remove residual hover bias. The final gains are `kp={final_pid["kp"]}`, `ki={final_pid["ki"]}`, `kd={final_pid["kd"]}`.

    ## Performance Results
    Worst post-gust MAE: {tuning["metrics"]["worst_post_gust_mae"]:.4f} m
    Max step-window MAE: {tuning["metrics"]["max_step_window_mae"]:.4f} m
    Final hover MAE: {tuning["metrics"]["final_hover_mae"]:.4f} m

    The resulting trajectory stays above ground, respects collective command limits, and returns to each hover window after the scheduled gust disturbances.
    '''
).strip() + "\n"

(ROOT / "pid_controller.py").write_text(pid_controller_code)
(ROOT / "altitude_controller.py").write_text(altitude_controller_code)
(ROOT / "simulate_altitude.py").write_text(simulate_code)
(ROOT / "altitude_tuning.yaml").write_text(yaml.safe_dump(tuning, sort_keys=False))
(ROOT / "altitude_hold_trace.csv").write_text(trace.to_csv(index=False))
(ROOT / "hover_analysis.md").write_text(report)
PY
