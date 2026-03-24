"""Autoscaling decision engine driven by YAML configuration."""

import math


class AutoscalingPolicyEngine:
    """Evaluate autoscaling actions from a nested configuration dict."""

    def __init__(self, config):
        self.config = config
        self.service = config["service"]
        self.replay = config["replay"]
        self.policies = config["policies"]
        self.slo = config["slo"]
        self.reset()

    def reset(self):
        self.instance_count = int(self.service["initial_instances"])
        self.last_scale_up_minute = None
        self.last_scale_down_minute = None

    def project_latency(self, request_rps, cpu_utilization_pct, instance_count):
        capacity = float(self.service["capacity_rps_per_instance"])
        base_latency = float(self.service["base_latency_ms"])
        overload_penalty = float(self.service["latency_penalty_ms_per_over_capacity"])
        cpu_penalty = float(self.service["cpu_penalty_ms_per_pct_over_60"])
        request_ratio = float(request_rps) / (float(instance_count) * capacity)
        overload = max(0.0, request_ratio - 0.7)
        cpu_over = max(0.0, float(cpu_utilization_pct) - 60.0)
        return base_latency + overload * overload_penalty + cpu_over * cpu_penalty

    def _cooldown_ready(self, minute, direction):
        cooldown = int(self.replay["cooldown_steps"][direction])
        previous = self.last_scale_up_minute if direction == "scale_up" else self.last_scale_down_minute
        if previous is None:
            return True
        dt = int(self.replay["dt_minutes"])
        elapsed_steps = (int(minute) - int(previous)) / dt
        return elapsed_steps >= cooldown

    def evaluate(self, minute, request_rps, cpu_utilization_pct):
        current_instances = int(self.instance_count)
        request_ratio = float(request_rps) / (
            float(current_instances) * float(self.service["capacity_rps_per_instance"])
        )
        projected_latency = self.project_latency(request_rps, cpu_utilization_pct, current_instances)

        action = "hold"
        cooldown_blocked = False
        up_policy = self.policies["scale_up"]
        down_policy = self.policies["scale_down"]

        scale_up_signal = (
            request_ratio >= float(up_policy["request_ratio_threshold"])
            or float(cpu_utilization_pct) >= float(up_policy["cpu_threshold_pct"])
            or projected_latency >= float(up_policy["latency_threshold_ms"])
        )
        scale_down_signal = (
            request_ratio <= float(down_policy["request_ratio_threshold"])
            and float(cpu_utilization_pct) <= float(down_policy["cpu_threshold_pct"])
            and projected_latency <= float(down_policy["latency_threshold_ms"])
        )

        if scale_up_signal:
            if self._cooldown_ready(minute, "scale_up"):
                target = min(
                    int(self.service["max_instances"]),
                    current_instances + int(up_policy["step"]),
                )
                if target > current_instances:
                    action = f"scale_up_{target - current_instances}"
                    self.instance_count = target
                    self.last_scale_up_minute = int(minute)
            else:
                cooldown_blocked = True
        elif scale_down_signal:
            if self._cooldown_ready(minute, "scale_down"):
                target = max(
                    int(self.service["min_instances"]),
                    current_instances - int(down_policy["step"]),
                )
                if target < current_instances:
                    action = f"scale_down_{current_instances - target}"
                    self.instance_count = target
                    self.last_scale_down_minute = int(minute)
            else:
                cooldown_blocked = True

        final_instances = int(self.instance_count)
        final_ratio = float(request_rps) / (
            float(final_instances) * float(self.service["capacity_rps_per_instance"])
        )
        final_latency = self.project_latency(request_rps, cpu_utilization_pct, final_instances)
        slo_met = final_latency <= float(self.slo["latency_p95_ms"])

        return {
            "action": action,
            "instance_count": final_instances,
            "request_ratio": round(final_ratio, 4),
            "projected_latency_ms": round(final_latency, 4),
            "slo_met": bool(slo_met),
            "cooldown_blocked": bool(cooldown_blocked),
        }
