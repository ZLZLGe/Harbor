#!/bin/bash
set -e

pip3 install --break-system-packages numpy==1.26.4 -q

python3 <<'PY'
import json
import math

import numpy as np


OUTPUT_FILE = "/root/traction_peak_stress_report.json"
NETWORK_FILE = "/root/rail_traction_network.json"
PATTERN_FILE = "/root/timetable_patterns.json"


def rounded(value):
    return round(float(value), 4)


with open(NETWORK_FILE, encoding="utf-8") as f:
    network = json.load(f)

with open(PATTERN_FILE, encoding="utf-8") as f:
    patterns = json.load(f)

base_mva = float(network["baseMVA"])
buses = network["buses"]
sections = network["sections"]
slack_bus = int(network["slack_bus"])
traction_substations = [int(bus) for bus in network["traction_substation_bus_ids"]]
loading_alert_pct = float(patterns["loading_alert_pct"])

bus_order = [int(bus["bus"]) for bus in buses]
bus_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_order)}
slack_idx = bus_to_idx[slack_bus]


def solve_case(entries):
    injections = {int(item["bus"]): float(item["net_injection_MW"]) for item in entries}
    injection_vector = np.array([injections[bus_id] for bus_id in bus_order], dtype=float)

    n_bus = len(bus_order)
    b_matrix = np.zeros((n_bus, n_bus), dtype=float)

    for section in sections:
        from_idx = bus_to_idx[int(section["from_bus"])]
        to_idx = bus_to_idx[int(section["to_bus"])]
        susceptance = 1.0 / float(section["x_pu"])

        b_matrix[from_idx, from_idx] += susceptance
        b_matrix[to_idx, to_idx] += susceptance
        b_matrix[from_idx, to_idx] -= susceptance
        b_matrix[to_idx, from_idx] -= susceptance

    keep = [idx for idx in range(n_bus) if idx != slack_idx]
    theta = np.zeros(n_bus, dtype=float)
    theta[keep] = np.linalg.solve(
        b_matrix[np.ix_(keep, keep)],
        injection_vector[keep] / base_mva,
    )

    substation_angles = [
        {"bus": bus_id, "angle_deg": rounded(theta[bus_to_idx[bus_id]] * 180.0 / math.pi)}
        for bus_id in traction_substations
    ]

    feeder_loadings = []
    loading_by_section = {}
    overloaded_sections = []

    for section in sections:
        from_bus = int(section["from_bus"])
        to_bus = int(section["to_bus"])
        from_idx = bus_to_idx[from_bus]
        to_idx = bus_to_idx[to_bus]
        flow_mw = (theta[from_idx] - theta[to_idx]) / float(section["x_pu"]) * base_mva
        rating_mw = float(section["rating_MW"])

        entry = {
            "section_id": section["section_id"],
            "from_bus": from_bus,
            "to_bus": to_bus,
            "corridor": section["corridor"],
            "section_type": section["section_type"],
            "flow_MW": rounded(flow_mw),
            "rating_MW": rounded(rating_mw),
            "loading_pct": rounded(abs(flow_mw) / rating_mw * 100.0),
        }
        feeder_loadings.append(entry)
        loading_by_section[section["section_id"]] = entry

        if entry["loading_pct"] >= loading_alert_pct:
            overloaded_sections.append(entry)

    return {
        "theta": theta,
        "substation_angles": substation_angles,
        "feeder_loadings": feeder_loadings,
        "loading_by_section": loading_by_section,
        "overloaded_sections": overloaded_sections,
    }


shoulder = solve_case(patterns["shoulder_bus_injections_MW"])
peak = solve_case(patterns["peak_headway_bus_injections_MW"])

largest_substation_angle_shifts = []
for bus_id in traction_substations:
    shoulder_angle = next(item["angle_deg"] for item in shoulder["substation_angles"] if item["bus"] == bus_id)
    peak_angle = next(item["angle_deg"] for item in peak["substation_angles"] if item["bus"] == bus_id)
    largest_substation_angle_shifts.append(
        {
            "bus": bus_id,
            "shoulder_angle_deg": shoulder_angle,
            "peak_headway_angle_deg": peak_angle,
            "absolute_shift_deg": rounded(abs(peak_angle - shoulder_angle)),
        }
    )

largest_substation_angle_shifts.sort(key=lambda item: (-item["absolute_shift_deg"], item["bus"]))

corridor_names = sorted({section["corridor"] for section in sections})
corridors_with_highest_incremental_stress = []

for corridor in corridor_names:
    corridor_sections = [section["section_id"] for section in sections if section["corridor"] == corridor]
    shoulder_entries = [shoulder["loading_by_section"][section_id] for section_id in corridor_sections]
    peak_entries = [peak["loading_by_section"][section_id] for section_id in corridor_sections]

    shoulder_max = max(entry["loading_pct"] for entry in shoulder_entries)
    peak_max = max(entry["loading_pct"] for entry in peak_entries)
    shoulder_limiting = sorted(
        [entry for entry in shoulder_entries if entry["loading_pct"] == shoulder_max],
        key=lambda entry: entry["section_id"],
    )[0]
    peak_limiting = sorted(
        [entry for entry in peak_entries if entry["loading_pct"] == peak_max],
        key=lambda entry: entry["section_id"],
    )[0]

    incremental_stress = rounded(peak_limiting["loading_pct"] - shoulder_limiting["loading_pct"])
    if incremental_stress <= 0:
        continue

    corridors_with_highest_incremental_stress.append(
        {
            "corridor": corridor,
            "shoulder_peak_loading_pct": shoulder_limiting["loading_pct"],
            "peak_headway_peak_loading_pct": peak_limiting["loading_pct"],
            "incremental_stress_pct": incremental_stress,
            "peak_limiting_section_id": peak_limiting["section_id"],
        }
    )

corridors_with_highest_incremental_stress.sort(
    key=lambda item: (-item["incremental_stress_pct"], item["corridor"])
)

shoulder_overload_ids = {entry["section_id"] for entry in shoulder["overloaded_sections"]}
peak_overload_ids = {entry["section_id"] for entry in peak["overloaded_sections"]}

report = {
    "scenario": {
        "name": patterns["scenario_name"],
        "slack_bus": slack_bus,
        "shoulder_pattern": patterns["shoulder_pattern_name"],
        "peak_headway_pattern": patterns["peak_pattern_name"],
        "traction_substation_bus_ids": traction_substations,
    },
    "shoulder_service": {
        "substation_angle_profile_deg": shoulder["substation_angles"],
        "feeder_loadings": shoulder["feeder_loadings"],
        "overloaded_sections": shoulder["overloaded_sections"],
    },
    "peak_headway_service": {
        "substation_angle_profile_deg": peak["substation_angles"],
        "feeder_loadings": peak["feeder_loadings"],
        "overloaded_sections": peak["overloaded_sections"],
    },
    "comparison": {
        "largest_substation_angle_shifts_deg": largest_substation_angle_shifts[
            : int(patterns["top_substation_shift_count"])
        ],
        "newly_overloaded_sections": sorted(peak_overload_ids - shoulder_overload_ids),
        "corridors_with_highest_incremental_stress": corridors_with_highest_incremental_stress[
            : int(patterns["top_corridor_count"])
        ],
    },
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
