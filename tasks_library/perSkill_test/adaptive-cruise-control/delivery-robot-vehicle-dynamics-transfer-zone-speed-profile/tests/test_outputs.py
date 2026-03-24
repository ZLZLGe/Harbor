import csv
import importlib.util
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path("/root")
SCRIPT_FILE = ROOT / "zone_speed_profile.py"
PROFILE_FILE = ROOT / "route_profile.yaml"
ZONE_FILE = ROOT / "zone_map.tsv"
OUTPUT_FILE = ROOT / "zone_speed_profile_metrics.yaml"


def round6(value):
    return round(float(value), 6)


def load_profile():
    with PROFILE_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_zones():
    zones = []
    with ZONE_FILE.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            zones.append(
                {
                    "zone_id": row["zone_id"],
                    "start_m": float(row["start_m"]),
                    "end_m": float(row["end_m"]),
                    "speed_limit_mps": float(row["speed_limit_mps"]),
                    "stop_id": row["stop_id"],
                    "stop_position_m": float(row["stop_position_m"]) if row["stop_position_m"] else None,
                }
            )
    return zones


def active_zone(position_m, zones):
    for index, zone in enumerate(zones):
        is_last = index == len(zones) - 1
        if zone["start_m"] <= position_m and (position_m < zone["end_m"] or (is_last and position_m <= zone["end_m"])):
            return zone
    raise ValueError(position_m)


def clamp(value, low, high):
    return max(low, min(high, value))


def earliest_constraint(position_m, zone, zones, served_stops):
    candidates = []
    if zone["stop_id"] and zone["stop_id"] not in served_stops and zone["stop_position_m"] <= position_m:
        candidates.append((zone["stop_position_m"], 0.0))

    for future_zone in zones:
        stop_id = future_zone["stop_id"]
        stop_position_m = future_zone["stop_position_m"]
        if stop_id and stop_id not in served_stops and stop_position_m is not None and stop_position_m > position_m:
            candidates.append((stop_position_m, 0.0))

    for index, _zone in enumerate(zones[:-1]):
        next_zone = zones[index + 1]
        if next_zone["start_m"] > position_m and next_zone["speed_limit_mps"] < zone["speed_limit_mps"]:
            candidates.append((next_zone["start_m"], next_zone["speed_limit_mps"]))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0]


def build_reference_payload():
    profile = load_profile()
    zones = load_zones()
    scenario = profile["scenario"]
    vehicle = profile["vehicle"]
    controller = profile["controller"]
    tolerance = profile["assessment"]["stop_error_tolerance_m"]

    dt_s = scenario["dt_s"]
    position_m = scenario["initial_position_m"]
    speed_mps = scenario["initial_speed_mps"]
    time_s = 0.0
    served_stops = set()
    rows = []
    stop_metrics = []
    mode_counter = Counter()
    final_stop_id = zones[-1]["stop_id"]

    while True:
        zone = active_zone(position_m, zones)
        constraint = earliest_constraint(position_m, zone, zones, served_stops)
        constraint_distance_m = None
        constraint_speed_mps = None
        braking_distance_m = 0.0
        if constraint is not None:
            constraint_position_m, constraint_speed_mps = constraint
            constraint_distance_m = max(constraint_position_m - position_m, 0.0)
            braking_distance_m = max(
                (speed_mps * speed_mps - constraint_speed_mps * constraint_speed_mps)
                / (2.0 * abs(vehicle["max_brake_mps2"])),
                0.0,
            )

        if (
            constraint is not None
            and constraint_distance_m <= braking_distance_m + controller["brake_margin_m"]
            and speed_mps > constraint_speed_mps + 0.05
        ):
            mode = "brake"
            command_accel_mps2 = max(
                vehicle["max_brake_mps2"],
                -controller["brake_gain"] * (speed_mps - constraint_speed_mps),
            )
        elif speed_mps < zone["speed_limit_mps"] - controller["cruise_tolerance_mps"]:
            mode = "accelerate"
            command_accel_mps2 = min(
                vehicle["max_accel_mps2"],
                controller["accel_gain"] * (zone["speed_limit_mps"] - speed_mps),
            )
        else:
            mode = "coast"
            command_accel_mps2 = 0.0

        net_accel_mps2 = (
            command_accel_mps2
            - vehicle["rolling_drag_mps2"]
            - vehicle["quadratic_drag_coeff"] * speed_mps * speed_mps
        )
        raw_speed_next_mps = clamp(
            speed_mps + net_accel_mps2 * dt_s,
            0.0,
            vehicle["max_speed_mps"],
        )
        raw_position_next_m = position_m + speed_mps * dt_s + 0.5 * net_accel_mps2 * dt_s * dt_s

        rows.append(
            {
                "time_s": time_s,
                "position_m": position_m,
                "speed_mps": speed_mps,
                "zone_id": zone["zone_id"],
                "speed_limit_mps": zone["speed_limit_mps"],
                "mode": mode,
            }
        )
        mode_counter[mode] += 1

        crossed_stop = None
        for candidate_zone in zones:
            stop_id = candidate_zone["stop_id"]
            stop_position_m = candidate_zone["stop_position_m"]
            if (
                stop_id
                and stop_id not in served_stops
                and stop_position_m is not None
                and position_m <= stop_position_m <= raw_position_next_m
            ):
                crossed_stop = candidate_zone
                break

        if crossed_stop is not None:
            served_stops.add(crossed_stop["stop_id"])
            stop_metrics.append(
                {
                    "stop_id": crossed_stop["stop_id"],
                    "target_position_m": round6(crossed_stop["stop_position_m"]),
                    "captured_time_s": round6(time_s + dt_s),
                    "position_error_m": round6(abs(raw_position_next_m - crossed_stop["stop_position_m"])),
                    "speed_error_mps": round6(raw_speed_next_mps),
                }
            )
            position_m = crossed_stop["stop_position_m"]
            speed_mps = 0.0
            time_s = round(time_s + dt_s, 10)
            if crossed_stop["stop_id"] == final_stop_id:
                break
            continue

        position_m = raw_position_next_m
        speed_mps = raw_speed_next_mps
        time_s = round(time_s + dt_s, 10)

    by_zone = defaultdict(list)
    for row in rows:
        by_zone[row["zone_id"]].append(row)

    zone_metrics = []
    for zone in zones:
        chunk = by_zone[zone["zone_id"]]
        zone_metrics.append(
            {
                "zone_id": zone["zone_id"],
                "entry_time_s": round6(chunk[0]["time_s"]),
                "exit_time_s": round6(chunk[-1]["time_s"]),
                "sample_count": len(chunk),
                "mean_speed_mps": round6(sum(row["speed_mps"] for row in chunk) / len(chunk)),
                "peak_speed_mps": round6(max(row["speed_mps"] for row in chunk)),
                "speed_limit_mps": round6(zone["speed_limit_mps"]),
            }
        )

    return {
        "scenario_id": scenario["id"],
        "time_step_s": round6(dt_s),
        "samples": len(rows),
        "mode_durations_s": {
            "accelerate": round6(mode_counter["accelerate"] * dt_s),
            "coast": round6(mode_counter["coast"] * dt_s),
            "brake": round6(mode_counter["brake"] * dt_s),
        },
        "zone_metrics": zone_metrics,
        "stop_metrics": stop_metrics,
        "summary": {
            "completed_stops": len(stop_metrics),
            "final_time_s": round6(time_s),
            "total_distance_m": round6(stop_metrics[-1]["target_position_m"]),
            "max_speed_mps": round6(max(row["speed_mps"] for row in rows)),
            "max_limit_excess_mps": round6(
                max(max(row["speed_mps"] - row["speed_limit_mps"], 0.0) for row in rows)
            ),
            "all_stops_within_tolerance": all(
                metric["position_error_m"] <= tolerance for metric in stop_metrics
            ),
            "max_stop_error_m": round6(max(metric["position_error_m"] for metric in stop_metrics)),
        },
    }


class TestInputs:
    def test_input_assets(self):
        profile = load_profile()
        zones = load_zones()

        assert profile["scenario"]["id"] == "orchard_loop_shift_b"
        assert profile["scenario"]["dt_s"] == 0.25
        assert profile["vehicle"]["max_accel_mps2"] == 1.4
        assert profile["vehicle"]["max_brake_mps2"] == -2.2
        assert profile["vehicle"]["quadratic_drag_coeff"] == 0.018
        assert profile["controller"]["brake_margin_m"] == 0.8
        assert profile["assessment"]["stop_error_tolerance_m"] == 0.6

        assert len(zones) == 6
        assert zones[0]["zone_id"] == "launch_lane"
        assert zones[2]["stop_id"] == "kiosk_buffer"
        assert zones[2]["stop_position_m"] == 58.0
        assert zones[-1]["stop_id"] == "library_buffer"
        assert zones[-1]["end_m"] == 126.0


class TestScript:
    def test_script_exists_and_imports(self):
        assert SCRIPT_FILE.exists(), "zone_speed_profile.py must exist"

        spec = importlib.util.spec_from_file_location("zone_speed_profile", SCRIPT_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


class TestOutput:
    def test_output_matches_reference(self):
        assert OUTPUT_FILE.exists(), "zone_speed_profile_metrics.yaml must be generated"
        with OUTPUT_FILE.open("r", encoding="utf-8") as handle:
            actual = yaml.safe_load(handle)

        expected = build_reference_payload()
        assert actual == expected

    def test_behavioral_landmarks(self):
        with OUTPUT_FILE.open("r", encoding="utf-8") as handle:
            actual = yaml.safe_load(handle)

        assert actual["samples"] == 279
        assert actual["mode_durations_s"] == {
            "accelerate": 32.0,
            "coast": 27.75,
            "brake": 10.0,
        }

        assert [item["zone_id"] for item in actual["zone_metrics"]] == [
            "launch_lane",
            "garden_walk",
            "kiosk_buffer",
            "quad_spur",
            "library_lane",
            "library_buffer",
        ]
        assert actual["stop_metrics"][0]["stop_id"] == "kiosk_buffer"
        assert actual["stop_metrics"][0]["captured_time_s"] == 32.0
        assert actual["stop_metrics"][1]["stop_id"] == "library_buffer"
        assert actual["stop_metrics"][1]["captured_time_s"] == 69.75

        summary = actual["summary"]
        assert summary["completed_stops"] == 2
        assert summary["final_time_s"] == 69.75
        assert summary["total_distance_m"] == 126.0
        assert summary["all_stops_within_tolerance"] is True
        assert summary["max_limit_excess_mps"] == 0.492921
