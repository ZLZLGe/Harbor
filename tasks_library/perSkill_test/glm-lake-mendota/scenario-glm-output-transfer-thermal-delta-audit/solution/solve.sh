#!/bin/bash
set -euo pipefail

mkdir -p /root/reports

python3 - <<'PY'
import json
import math
import struct
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path("/root/config/audit_spec.json")
BASELINE_PATH = Path("/root/data/thermal_baseline_output.nc")
INTERVENTION_PATH = Path("/root/data/thermal_intervention_output.nc")
OUTPUT_PATH = Path("/root/reports/scenario_delta_summary.json")


def pad4(length: int) -> int:
    return (4 - (length % 4)) % 4


class NetCDFClassicReader:
    def __init__(self, path: Path):
        self.data = path.read_bytes()
        self.offset = 0

    def read(self, length: int) -> bytes:
        chunk = self.data[self.offset : self.offset + length]
        self.offset += length
        return chunk

    def read_u32(self) -> int:
        return struct.unpack(">I", self.read(4))[0]

    def read_name(self) -> str:
        length = self.read_u32()
        raw = self.read(length)
        self.read(pad4(length))
        return raw.decode("ascii")

    def read_list_header(self, expected_tag: int) -> int:
        tag = self.read_u32()
        count = self.read_u32()
        if tag == 0 and count == 0:
            return 0
        if tag != expected_tag:
            raise ValueError(f"Unexpected NetCDF tag: {tag} != {expected_tag}")
        return count

    def skip_attributes(self) -> None:
        attr_count = self.read_list_header(12)
        for _ in range(attr_count):
            self.read_name()
            value_type = self.read_u32()
            value_count = self.read_u32()
            value_size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 4, 6: 8}[value_type]
            self.read(value_count * value_size)
            self.read(pad4(value_count * value_size))


def reshape(values, shape):
    if not shape:
        return values[0]
    if len(shape) == 1:
        return list(values)
    step = math.prod(shape[1:])
    return [reshape(values[index * step : (index + 1) * step], shape[1:]) for index in range(shape[0])]


def read_glm_output(path: Path):
    reader = NetCDFClassicReader(path)
    if reader.read(4) != b"CDF\x01":
        raise ValueError("Only classic NetCDF files are supported")

    reader.read_u32()

    dim_count = reader.read_list_header(10)
    dims = []
    for _ in range(dim_count):
        dims.append((reader.read_name(), reader.read_u32()))

    reader.skip_attributes()

    variable_count = reader.read_list_header(11)
    variables = {}
    for _ in range(variable_count):
        name = reader.read_name()
        ndims = reader.read_u32()
        dim_ids = [reader.read_u32() for _ in range(ndims)]
        reader.skip_attributes()
        value_type = reader.read_u32()
        value_size = reader.read_u32()
        begin = reader.read_u32()

        if value_type != 5:
            raise ValueError("Only float variables are supported")

        shape = [dims[dim_id][1] for dim_id in dim_ids]
        count = math.prod(shape) if shape else 1
        raw = reader.data[begin : begin + count * 4]
        values = struct.unpack(">" + "f" * count, raw)
        variables[name] = reshape(values, shape)

    return variables


def choose_temperature(profile_depths, profile_temps, focus_depth):
    best = None
    for depth_from_surface, temp_c in zip(profile_depths, profile_temps):
        candidate = (abs(depth_from_surface - focus_depth), -depth_from_surface, temp_c)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return best[2]


def deviation_from_window(temp_c, min_c, max_c):
    if temp_c < min_c:
        return min_c - temp_c
    if temp_c > max_c:
        return temp_c - max_c
    return 0.0


def extract_series(path: Path, start_time: datetime, lake_depth_m: float, focus_depths):
    nc = read_glm_output(path)
    series = {}
    for time_index, hour_offset in enumerate(nc["time"]):
        timestamp = start_time + timedelta(hours=float(hour_offset))
        profile_depths = []
        profile_temps = []
        for layer_index in range(len(nc["z"][time_index])):
            z_value = nc["z"][time_index][layer_index][0][0]
            temp_value = nc["temp"][time_index][layer_index][0][0]
            depth_from_surface = lake_depth_m - float(z_value)
            profile_depths.append(depth_from_surface)
            profile_temps.append(float(temp_value))

        for focus_depth in focus_depths:
            series[(timestamp, float(focus_depth))] = choose_temperature(profile_depths, profile_temps, float(focus_depth))
    return series


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    focus_depths = sorted(float(depth) for depth in config["focus_depths_m"])
    target_min = float(config["target_temperature_window_c"]["min"])
    target_max = float(config["target_temperature_window_c"]["max"])
    lake_depth_m = float(config["lake_depth_m"])
    start_time = datetime.fromisoformat(config["simulation_start"])

    baseline_series = extract_series(BASELINE_PATH, start_time, lake_depth_m, focus_depths)
    intervention_series = extract_series(INTERVENTION_PATH, start_time, lake_depth_m, focus_depths)
    matched_keys = sorted(set(baseline_series) & set(intervention_series))

    monthly_groups = {}
    for timestamp, focus_depth in matched_keys:
        month = timestamp.strftime("%Y-%m")
        group = monthly_groups.setdefault((month, focus_depth), {"baseline": [], "intervention": []})
        group["baseline"].append(baseline_series[(timestamp, focus_depth)])
        group["intervention"].append(intervention_series[(timestamp, focus_depth)])

    monthly_depth_deltas = []
    for month, focus_depth in sorted(monthly_groups):
        baseline_mean = sum(monthly_groups[(month, focus_depth)]["baseline"]) / len(monthly_groups[(month, focus_depth)]["baseline"])
        intervention_mean = sum(monthly_groups[(month, focus_depth)]["intervention"]) / len(monthly_groups[(month, focus_depth)]["intervention"])
        monthly_depth_deltas.append(
            {
                "month": month,
                "depth_m": focus_depth,
                "baseline_mean_temp_c": baseline_mean,
                "intervention_mean_temp_c": intervention_mean,
                "delta_c": intervention_mean - baseline_mean,
            }
        )

    summer_start = datetime.fromisoformat(config["summer_start_date"] + "T00:00:00")
    summer_end = datetime.fromisoformat(config["summer_end_date"] + "T23:59:59")
    summer_bottom_depth_m = max(focus_depths)
    baseline_bottom = []
    intervention_bottom = []
    for timestamp, focus_depth in matched_keys:
        if focus_depth != summer_bottom_depth_m:
            continue
        if summer_start <= timestamp <= summer_end:
            baseline_bottom.append(baseline_series[(timestamp, focus_depth)])
            intervention_bottom.append(intervention_series[(timestamp, focus_depth)])

    summer_bottom_cooling_c = (
        (sum(baseline_bottom) / len(baseline_bottom)) - (sum(intervention_bottom) / len(intervention_bottom))
    )

    closer_to_target_by_depth = []
    baseline_total = 0.0
    intervention_total = 0.0
    for focus_depth in focus_depths:
        baseline_deviations = []
        intervention_deviations = []
        for timestamp, candidate_depth in matched_keys:
            if candidate_depth != focus_depth:
                continue
            baseline_deviations.append(
                deviation_from_window(baseline_series[(timestamp, focus_depth)], target_min, target_max)
            )
            intervention_deviations.append(
                deviation_from_window(intervention_series[(timestamp, focus_depth)], target_min, target_max)
            )

        baseline_mean_deviation = sum(baseline_deviations) / len(baseline_deviations)
        intervention_mean_deviation = sum(intervention_deviations) / len(intervention_deviations)
        baseline_total += baseline_mean_deviation
        intervention_total += intervention_mean_deviation

        if baseline_mean_deviation < intervention_mean_deviation:
            preferred = "baseline"
        elif intervention_mean_deviation < baseline_mean_deviation:
            preferred = "intervention"
        else:
            preferred = "tie"

        closer_to_target_by_depth.append(
            {
                "depth_m": focus_depth,
                "baseline_mean_abs_deviation_c": baseline_mean_deviation,
                "intervention_mean_abs_deviation_c": intervention_mean_deviation,
                "preferred_scenario": preferred,
            }
        )

    if baseline_total < intervention_total:
        overall_preferred = "baseline"
    elif intervention_total < baseline_total:
        overall_preferred = "intervention"
    else:
        overall_preferred = "tie"

    report = {
        "site_name": str(config["site_name"]),
        "focus_depths_m": focus_depths,
        "target_temperature_window_c": {
            "min": target_min,
            "max": target_max,
        },
        "monthly_depth_deltas": monthly_depth_deltas,
        "summer_bottom_depth_m": summer_bottom_depth_m,
        "summer_bottom_cooling_c": summer_bottom_cooling_c,
        "closer_to_target_by_depth": closer_to_target_by_depth,
        "overall_preferred_scenario": overall_preferred,
    }

    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


main()
PY
