"""Tank level controller built on a PID loop."""

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
