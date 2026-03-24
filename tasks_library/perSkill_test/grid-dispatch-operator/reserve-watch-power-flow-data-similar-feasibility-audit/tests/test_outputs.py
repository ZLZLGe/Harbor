import json
import os

import numpy as np
import pytest

OUTPUT_FILE = "/root/dispatch_audit.json"
NETWORK_FILE = "/root/network_snapshot.json"
SCHEDULE_FILE = "/root/proposed_schedule.json"


def round2(value):
    return round(float(value), 2)


@pytest.fixture(scope="module")
def audit():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def schedule():
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected(network, schedule):
    base_mva = float(network["baseMVA"])
    buses = np.array(network["bus"], dtype=float)
    gens = np.array(network["gen"], dtype=float)
    branches = np.array(network["branch"], dtype=float)
    reserve_capacity = np.array(network["reserve_capacity"], dtype=float)
    schedule_rows = schedule["generator_schedule"]

    assert len(schedule_rows) == len(gens), "Schedule length must match generator rows"
    for i, row in enumerate(schedule_rows):
        assert int(row["id"]) == i + 1, f"Schedule id mismatch at row {i + 1}"
        assert int(row["bus"]) == int(gens[i, 0]), f"Schedule bus mismatch at row {i + 1}"

    output_mw = np.array([row["output_MW"] for row in schedule_rows], dtype=float)
    reserve_mw = np.array([row["reserve_MW"] for row in schedule_rows], dtype=float)

    reserve_capacity_violations = []
    coupling_violations = []
    for i, row in enumerate(schedule_rows):
        reserve_excess = reserve_mw[i] - reserve_capacity[i]
        if reserve_excess > 1e-6:
            reserve_capacity_violations.append(
                {
                    "id": int(row["id"]),
                    "bus": int(gens[i, 0]),
                    "scheduled_reserve_MW": round2(reserve_mw[i]),
                    "reserve_capacity_MW": round2(reserve_capacity[i]),
                    "excess_MW": round2(reserve_excess),
                }
            )

        coupling_excess = output_mw[i] + reserve_mw[i] - gens[i, 8]
        if coupling_excess > 1e-6:
            coupling_violations.append(
                {
                    "id": int(row["id"]),
                    "bus": int(gens[i, 0]),
                    "scheduled_output_MW": round2(output_mw[i]),
                    "scheduled_reserve_MW": round2(reserve_mw[i]),
                    "pmax_MW": round2(gens[i, 8]),
                    "excess_MW": round2(coupling_excess),
                }
            )

    reserve_capacity_violations.sort(key=lambda row: row["id"])
    coupling_violations.sort(key=lambda row: (-row["excess_MW"], row["id"]))

    n_bus = len(buses)
    bus_num_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
    B = np.zeros((n_bus, n_bus), dtype=float)
    for branch in branches:
        reactance = float(branch[3])
        if reactance == 0:
            continue
        f_idx = bus_num_to_idx[int(branch[0])]
        t_idx = bus_num_to_idx[int(branch[1])]
        susceptance = 1.0 / reactance
        B[f_idx, f_idx] += susceptance
        B[t_idx, t_idx] += susceptance
        B[f_idx, t_idx] -= susceptance
        B[t_idx, f_idx] -= susceptance

    injections_mw = np.zeros(n_bus, dtype=float)
    for i, gen in enumerate(gens):
        injections_mw[bus_num_to_idx[int(gen[0])]] += output_mw[i]
    injections_mw -= buses[:, 2]

    slack_idx = next(i for i, bus in enumerate(buses) if int(bus[1]) == 3)
    injections_mw[slack_idx] -= injections_mw.sum()

    mask = np.ones(n_bus, dtype=bool)
    mask[slack_idx] = False
    theta = np.zeros(n_bus, dtype=float)
    theta[mask] = np.linalg.solve(B[np.ix_(mask, mask)], injections_mw[mask] / base_mva)

    branch_rows = []
    for branch in branches:
        f_idx = bus_num_to_idx[int(branch[0])]
        t_idx = bus_num_to_idx[int(branch[1])]
        reactance = float(branch[3])
        rating = float(branch[5])
        flow_mw = 0.0 if reactance == 0 else (1.0 / reactance) * (theta[f_idx] - theta[t_idx]) * base_mva
        loading_pct = 0.0 if rating <= 0 else abs(flow_mw) / rating * 100.0
        branch_rows.append(
            {
                "from": int(branch[0]),
                "to": int(branch[1]),
                "flow_MW": round2(flow_mw),
                "rating_MW": round2(rating),
                "loading_pct": round2(loading_pct),
            }
        )
    top3 = sorted(branch_rows, key=lambda row: (-row["loading_pct"], row["from"], row["to"]))[:3]

    total_load = float(buses[:, 2].sum())
    total_generation = float(output_mw.sum())
    total_reserve = float(reserve_mw.sum())
    reserve_requirement = float(network["reserve_requirement"])

    return {
        "checks": {
            "generation_matches_load": round2(total_generation) == round2(total_load),
            "reserve_requirement_met": total_reserve + 1e-6 >= reserve_requirement,
            "all_reserves_within_generator_limits": len(reserve_capacity_violations) == 0,
            "all_generators_within_capacity_coupling": len(coupling_violations) == 0,
        },
        "totals": {
            "load_MW": round2(total_load),
            "scheduled_generation_MW": round2(total_generation),
            "generation_minus_load_MW": round2(total_generation - total_load),
            "scheduled_reserve_MW": round2(total_reserve),
            "reserve_requirement_MW": round2(reserve_requirement),
            "reserve_shortfall_MW": round2(max(reserve_requirement - total_reserve, 0.0)),
        },
        "reserve_capacity_violations": reserve_capacity_violations,
        "capacity_coupling_violations": coupling_violations,
        "branch_loading_top3": top3,
    }


class TestSchema:
    def test_top_level_fields(self, audit):
        assert set(audit.keys()) == {
            "checks",
            "totals",
            "reserve_capacity_violations",
            "capacity_coupling_violations",
            "branch_loading_top3",
        }

    def test_checks_schema(self, audit):
        expected_keys = {
            "generation_matches_load",
            "reserve_requirement_met",
            "all_reserves_within_generator_limits",
            "all_generators_within_capacity_coupling",
        }
        assert set(audit["checks"].keys()) == expected_keys
        assert all(isinstance(audit["checks"][key], bool) for key in expected_keys)

    def test_totals_schema(self, audit):
        expected_keys = {
            "load_MW",
            "scheduled_generation_MW",
            "generation_minus_load_MW",
            "scheduled_reserve_MW",
            "reserve_requirement_MW",
            "reserve_shortfall_MW",
        }
        assert set(audit["totals"].keys()) == expected_keys


class TestAuditValues:
    def test_checks_match_expected(self, audit, expected):
        assert audit["checks"] == expected["checks"]

    def test_totals_match_expected(self, audit, expected):
        assert audit["totals"] == expected["totals"]

    def test_reserve_capacity_violations(self, audit, expected):
        assert audit["reserve_capacity_violations"] == expected["reserve_capacity_violations"]

    def test_capacity_coupling_violations(self, audit, expected):
        assert audit["capacity_coupling_violations"] == expected["capacity_coupling_violations"]

    def test_branch_loading_top3(self, audit, expected):
        assert audit["branch_loading_top3"] == expected["branch_loading_top3"]

    def test_branch_loading_is_sorted(self, audit):
        loadings = [row["loading_pct"] for row in audit["branch_loading_top3"]]
        assert loadings == sorted(loadings, reverse=True)

    def test_known_violation_and_shortfall_pattern(self, audit):
        assert audit["checks"]["generation_matches_load"] is True
        assert audit["checks"]["reserve_requirement_met"] is False
        assert audit["checks"]["all_reserves_within_generator_limits"] is True
        assert audit["checks"]["all_generators_within_capacity_coupling"] is False
        assert [row["id"] for row in audit["capacity_coupling_violations"]] == [90, 430, 212]
