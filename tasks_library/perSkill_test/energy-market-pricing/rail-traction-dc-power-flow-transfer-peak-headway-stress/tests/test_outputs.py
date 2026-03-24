import json
import math
import os

import numpy as np
import pytest

OUTPUT_FILE = "/root/traction_peak_stress_report.json"
NETWORK_FILE = "/root/rail_traction_network.json"
PATTERN_FILE = "/root/timetable_patterns.json"


def rounded(value):
    return round(float(value), 4)


def compute_expected_report(network, patterns):
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

    corridors_with_highest_incremental_stress = []
    for corridor in sorted({section["corridor"] for section in sections}):
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

    return {
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


@pytest.fixture(scope="module")
def report():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def patterns():
    with open(PATTERN_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_report(network, patterns):
    return compute_expected_report(network, patterns)


class TestSchema:
    def test_top_level_fields(self, report):
        assert sorted(report.keys()) == ["comparison", "peak_headway_service", "scenario", "shoulder_service"]

    def test_list_lengths(self, report, network, patterns):
        section_count = len(network["sections"])
        substation_count = len(network["traction_substation_bus_ids"])

        assert len(report["shoulder_service"]["substation_angle_profile_deg"]) == substation_count
        assert len(report["peak_headway_service"]["substation_angle_profile_deg"]) == substation_count
        assert len(report["shoulder_service"]["feeder_loadings"]) == section_count
        assert len(report["peak_headway_service"]["feeder_loadings"]) == section_count
        assert len(report["comparison"]["largest_substation_angle_shifts_deg"]) == min(
            substation_count, int(patterns["top_substation_shift_count"])
        )


class TestNumerics:
    def test_report_matches_expected(self, report, expected_report):
        assert report == expected_report

    def test_newly_overloaded_sections(self, report):
        assert report["comparison"]["newly_overloaded_sections"] == ["CX-2", "EL-1", "SB-2"]
        assert report["shoulder_service"]["overloaded_sections"] == []
        assert [entry["section_id"] for entry in report["peak_headway_service"]["overloaded_sections"]] == [
            "EL-1",
            "SB-2",
            "CX-2",
        ]

    def test_top_corridor_stress(self, report):
        top_corridor = report["comparison"]["corridors_with_highest_incremental_stress"][0]
        assert top_corridor["corridor"] == "South Branch"
        assert top_corridor["incremental_stress_pct"] == pytest.approx(32.2992, abs=1e-4)

    def test_largest_substation_shift(self, report):
        top_entry = report["comparison"]["largest_substation_angle_shifts_deg"][0]
        assert top_entry["bus"] == 8330
        assert top_entry["absolute_shift_deg"] == pytest.approx(1.2012, abs=1e-4)
