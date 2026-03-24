#!/bin/bash

set -euo pipefail

TASK_ROOT="${TASK_ROOT:-/root}"
cd "$TASK_ROOT"

python3 <<'PY'
from pathlib import Path


zone_controller_code = '''"""Greenhouse zone climate controller.""" 


class ZoneClimateController:
    """Compute bounded heater, vent, and mister commands for one zone."""

    def __init__(self, zone_name, zone_policy, global_config):
        self.zone_name = zone_name
        self.zone_policy = zone_policy
        self.global_config = global_config
        self.reset()

    def reset(self):
        self.last_commands = {
            "heater_kw": 0.0,
            "vent_pct": 0.0,
            "mister_lpm": 0.0,
        }

    def compute_controls(
        self,
        estimated_temp_c,
        estimated_humidity_pct,
        outside_temp_c,
        outside_humidity_pct,
        solar_wm2,
        fallback_active,
    ):
        targets = self.zone_policy["targets"]
        limits = self.zone_policy["limits"]
        fallback = self.zone_policy["fallback"]

        temp_min = float(targets["temperature_c"]["min"])
        temp_max = float(targets["temperature_c"]["max"])
        hum_min = float(targets["humidity_pct"]["min"])
        hum_max = float(targets["humidity_pct"]["max"])

        temp_mid = (temp_min + temp_max) / 2.0
        hum_mid = (hum_min + hum_max) / 2.0

        heater_kw = max(0.0, (temp_mid - estimated_temp_c) * 2.1)
        heater_kw = min(float(limits["heater_kw_max"]), heater_kw)

        vent_pct = max(
            0.0,
            (estimated_temp_c - temp_mid) * 7.5,
            (estimated_humidity_pct - hum_mid) * 1.8,
            (solar_wm2 / 200.0) if estimated_temp_c >= temp_max else 0.0,
        )
        vent_pct = min(float(limits["vent_pct_max"]), vent_pct)
        if heater_kw > 0.0:
            vent_pct = min(vent_pct, float(fallback["safe_vent_pct"]))

        mister_lpm = max(0.0, (hum_mid - estimated_humidity_pct) * 0.22)
        mister_lpm = min(float(limits["mister_lpm_max"]), mister_lpm)
        if estimated_humidity_pct >= hum_max:
            mister_lpm = 0.0
        if estimated_temp_c >= temp_max:
            heater_kw = 0.0

        if fallback_active:
            heater_kw = max(heater_kw, float(fallback["safe_heater_kw"]))
            if estimated_humidity_pct < hum_min:
                mister_lpm = max(mister_lpm, float(fallback["safe_mister_lpm"]))

        self.last_commands = {
            "heater_kw": round(heater_kw, 4),
            "vent_pct": round(vent_pct, 4),
            "mister_lpm": round(mister_lpm, 4),
        }
        return dict(self.last_commands)
'''


greenhouse_replay_code = '''"""Replay greenhouse climate control from YAML policies and a CSV trace.""" 

import csv
from pathlib import Path

import yaml

from zone_controller import ZoneClimateController


BASE_DIR = Path(__file__).resolve().parent


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_trace(path):
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def maybe_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def round_metric(value):
    return round(float(value), 4)


def main():
    config = load_yaml(BASE_DIR / "greenhouse_policies.yaml")["greenhouse"]
    trace_rows = load_trace(BASE_DIR / "sensor_trace.csv")

    controllers = {}
    state_by_zone = {}
    last_valid_sensor = {}
    missing_by_zone = {}
    metrics = {}
    outputs = []

    for zone_name, zone_policy in config["zones"].items():
        controllers[zone_name] = ZoneClimateController(zone_name, zone_policy, config)
        state_by_zone[zone_name] = {
            "temperature_c": float(zone_policy["initial_state"]["temperature_c"]),
            "humidity_pct": float(zone_policy["initial_state"]["humidity_pct"]),
        }
        last_valid_sensor[zone_name] = None
        missing_by_zone[zone_name] = 0
        metrics[zone_name] = {
            "temp_hits": 0,
            "humidity_hits": 0,
            "samples": 0,
            "fallback_events": 0,
            "max_temp_deviation": 0.0,
            "max_humidity_deviation": 0.0,
        }

    for row in trace_rows:
        zone_name = row["zone"]
        zone_policy = config["zones"][zone_name]
        state = state_by_zone[zone_name]
        zone_metrics = metrics[zone_name]
        max_missing = int(config["fallback"]["max_missing_steps"])

        observed_temp = maybe_float(row["temp_sensor_c"])
        observed_humidity = maybe_float(row["humidity_sensor_pct"])
        fallback_active = observed_temp is None or observed_humidity is None

        if fallback_active:
            zone_metrics["fallback_events"] += 1
            if last_valid_sensor[zone_name] is not None and missing_by_zone[zone_name] < max_missing:
                observed_temp, observed_humidity = last_valid_sensor[zone_name]
                missing_by_zone[zone_name] += 1
            else:
                observed_temp = float(state["temperature_c"])
                observed_humidity = float(state["humidity_pct"])
        else:
            last_valid_sensor[zone_name] = (observed_temp, observed_humidity)
            missing_by_zone[zone_name] = 0

        blend = float(config["replay"]["sensor_blend"])
        estimated_temp = blend * observed_temp + (1.0 - blend) * float(state["temperature_c"])
        estimated_humidity = blend * observed_humidity + (1.0 - blend) * float(state["humidity_pct"])

        controls = controllers[zone_name].compute_controls(
            estimated_temp_c=estimated_temp,
            estimated_humidity_pct=estimated_humidity,
            outside_temp_c=float(row["outside_temp_c"]),
            outside_humidity_pct=float(row["outside_humidity_pct"]),
            solar_wm2=float(row["solar_wm2"]),
            fallback_active=fallback_active,
        )

        temp_model = config["model"]["temperature"]
        humidity_model = config["model"]["humidity"]

        next_temp = (
            estimated_temp
            + float(temp_model["heater_gain_per_kw"]) * controls["heater_kw"]
            - float(temp_model["vent_cooling_per_pct"]) * controls["vent_pct"]
            - float(temp_model["outside_leak_per_step"]) * (estimated_temp - float(row["outside_temp_c"]))
            + float(temp_model["solar_gain_per_wm2"]) * float(row["solar_wm2"])
        )
        next_humidity = (
            estimated_humidity
            + float(humidity_model["mister_gain_per_lpm"]) * controls["mister_lpm"]
            - float(humidity_model["vent_drying_per_pct"]) * controls["vent_pct"]
            - float(humidity_model["outside_leak_per_step"]) * (estimated_humidity - float(row["outside_humidity_pct"]))
        )
        next_humidity = max(0.0, min(100.0, next_humidity))

        temp_band = zone_policy["targets"]["temperature_c"]
        humidity_band = zone_policy["targets"]["humidity_pct"]
        temp_in_band = float(temp_band["min"]) <= next_temp <= float(temp_band["max"])
        humidity_in_band = float(humidity_band["min"]) <= next_humidity <= float(humidity_band["max"])

        zone_metrics["samples"] += 1
        zone_metrics["temp_hits"] += int(temp_in_band)
        zone_metrics["humidity_hits"] += int(humidity_in_band)
        zone_metrics["max_temp_deviation"] = max(
            zone_metrics["max_temp_deviation"],
            max(float(temp_band["min"]) - next_temp, 0.0, next_temp - float(temp_band["max"])),
        )
        zone_metrics["max_humidity_deviation"] = max(
            zone_metrics["max_humidity_deviation"],
            max(
                float(humidity_band["min"]) - next_humidity,
                0.0,
                next_humidity - float(humidity_band["max"]),
            ),
        )

        state_by_zone[zone_name] = {
            "temperature_c": next_temp,
            "humidity_pct": next_humidity,
        }

        outputs.append(
            {
                "time_min": row["time_min"],
                "zone": zone_name,
                "estimated_temp_c": f"{next_temp:.4f}",
                "estimated_humidity_pct": f"{next_humidity:.4f}",
                "heater_kw": f"{controls['heater_kw']:.4f}",
                "vent_pct": f"{controls['vent_pct']:.4f}",
                "mister_lpm": f"{controls['mister_lpm']:.4f}",
                "temp_in_band": str(bool(temp_in_band)).lower(),
                "humidity_in_band": str(bool(humidity_in_band)).lower(),
                "fallback_applied": str(bool(fallback_active)).lower(),
            }
        )

    with open(BASE_DIR / "climate_simulation.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "time_min",
                "zone",
                "estimated_temp_c",
                "estimated_humidity_pct",
                "heater_kw",
                "vent_pct",
                "mister_lpm",
                "temp_in_band",
                "humidity_in_band",
                "fallback_applied",
            ],
        )
        writer.writeheader()
        writer.writerows(outputs)

    strategy = {
        "replay": {
            "rows_processed": len(trace_rows),
            "time_step_minutes": int(config["replay"]["dt_minutes"]),
        },
        "zones": {},
        "overall": {
            "zones_simulated": len(config["zones"]),
            "all_temperature_ratios_ok": True,
            "all_humidity_ratios_ok": True,
            "all_constraints_ok": True,
        },
    }

    report_lines = [
        "# Greenhouse Climate Replay Report",
        "",
        "## system design",
        "A per-zone controller reads the nested policy YAML, blends sensor observations with simulated state, and clamps heater, vent, and mister outputs to configured limits.",
        "",
        "## fallback handling",
        "Blank sensor cells reuse the last valid observation for the configured number of missing steps, then fall back to the estimated state while keeping safe actuator floors from the YAML policy.",
        "",
        "## replay results",
    ]

    for zone_name, zone_policy in config["zones"].items():
        zone_metrics = metrics[zone_name]
        samples = zone_metrics["samples"]
        temp_ratio = zone_metrics["temp_hits"] / samples
        humidity_ratio = zone_metrics["humidity_hits"] / samples
        temp_band = zone_policy["targets"]["temperature_c"]
        humidity_band = zone_policy["targets"]["humidity_pct"]
        limits = zone_policy["limits"]
        state = state_by_zone[zone_name]
        temp_band_width = float(temp_band["max"]) - float(temp_band["min"])
        humidity_band_width = float(humidity_band["max"]) - float(humidity_band["min"])

        strategy["zones"][zone_name] = {
            "crop": zone_policy["crop"],
            "target_band": {
                "temperature_c": {
                    "min": float(temp_band["min"]),
                    "max": float(temp_band["max"]),
                },
                "humidity_pct": {
                    "min": float(humidity_band["min"]),
                    "max": float(humidity_band["max"]),
                },
            },
            "actuator_limits": {
                "heater_kw_max": float(limits["heater_kw_max"]),
                "vent_pct_max": float(limits["vent_pct_max"]),
                "mister_lpm_max": float(limits["mister_lpm_max"]),
            },
            "fallback_mode": {
                "missing_sensor_policy": "hold-last-then-estimate",
                "max_missing_steps": int(config["fallback"]["max_missing_steps"]),
            },
            "derived_strategy": {
                "temperature_gain_kw_per_c": round_metric(float(limits["heater_kw_max"]) / temp_band_width),
                "vent_gain_pct_per_c": round_metric(float(limits["vent_pct_max"]) / temp_band_width),
                "mister_gain_lpm_per_pct": round_metric(float(limits["mister_lpm_max"]) / humidity_band_width),
            },
            "metrics": {
                "temperature_in_band_ratio": round_metric(temp_ratio),
                "humidity_in_band_ratio": round_metric(humidity_ratio),
                "fallback_events": int(zone_metrics["fallback_events"]),
                "max_temperature_deviation_c": round_metric(zone_metrics["max_temp_deviation"]),
                "max_humidity_deviation_pct": round_metric(zone_metrics["max_humidity_deviation"]),
                "final_estimated_temperature_c": round_metric(state["temperature_c"]),
                "final_estimated_humidity_pct": round_metric(state["humidity_pct"]),
            },
        }

        strategy["overall"]["all_temperature_ratios_ok"] = (
            strategy["overall"]["all_temperature_ratios_ok"] and temp_ratio >= 0.75
        )
        strategy["overall"]["all_humidity_ratios_ok"] = (
            strategy["overall"]["all_humidity_ratios_ok"] and humidity_ratio >= 0.9
        )
        strategy["overall"]["all_constraints_ok"] = (
            strategy["overall"]["all_constraints_ok"]
            and zone_metrics["fallback_events"] >= 1
            and temp_ratio >= 0.75
            and humidity_ratio >= 0.9
        )

        report_lines.append(
            "- {zone}: temp ratio={temp_ratio:.3f}, humidity ratio={humidity_ratio:.3f}, "
            "fallback events={fallbacks}, final temp={temp:.2f}C, final humidity={humidity:.2f}%".format(
                zone=zone_name,
                temp_ratio=temp_ratio,
                humidity_ratio=humidity_ratio,
                fallbacks=zone_metrics["fallback_events"],
                temp=state["temperature_c"],
                humidity=state["humidity_pct"],
            )
        )

    with open(BASE_DIR / "greenhouse_strategy.yaml", "w", encoding="utf-8") as handle:
        yaml.dump(strategy, handle, default_flow_style=False, sort_keys=False)

    with open(BASE_DIR / "greenhouse_report.md", "w", encoding="utf-8") as handle:
        handle.write("\\n".join(report_lines) + "\\n")


if __name__ == "__main__":
    main()
'''


Path("zone_controller.py").write_text(zone_controller_code, encoding="utf-8")
Path("greenhouse_replay.py").write_text(greenhouse_replay_code, encoding="utf-8")
PY

python3 greenhouse_replay.py
