import json
import os

import pytest

OUTPUT_FILE = "/root/interconnection_choice.json"
NETWORK_FILE = "/root/planning_snapshot.json"
CONFIG_FILE = "/root/interconnection_candidates.json"

BUS_101 = 101
BUS_205 = 205
BUS_330 = 330
BUS_440 = 440
BUS_550 = 550


def round2(value):
    return round(float(value) + 1e-9, 2)


@pytest.fixture(scope="module")
def output():
    assert os.path.exists(OUTPUT_FILE), f"Missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def network():
    with open(NETWORK_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference(network, config):
    bus_load = {int(row[0]): float(row[2]) for row in network["bus"]}
    bus_numbers = sorted(bus_load)
    gen_cost = {
        int(network["gen"][idx][0]): float(network["gencost"][idx][5])
        for idx in range(len(network["gen"]))
    }
    pmax = {int(row[0]): float(row[8]) for row in network["gen"]}
    reserve_capacity = {
        int(network["gen"][idx][0]): float(network["reserve_capacity"][idx])
        for idx in range(len(network["gen"]))
    }
    reserve_requirement = float(network["reserve_requirement"])
    branch_limits = {(int(row[0]), int(row[1])): float(row[5]) for row in network["branch"]}

    binding_threshold = float(config["binding_threshold_pct"])
    added_load_mw = float(config["added_load_MW"])
    price_diffusion_threshold = float(config["price_diffusion_threshold_dollars_per_MWh"])

    def solve_case(scenario_id, extra_bus=None):
        loads = dict(bus_load)
        if extra_bus is not None:
            loads[extra_bus] += added_load_mw

        limit_101_205 = branch_limits[(BUS_101, BUS_205)]
        limit_205_330 = branch_limits[(BUS_205, BUS_330)]
        limit_330_440 = branch_limits[(BUS_330, BUS_440)]
        limit_330_550 = branch_limits[(BUS_330, BUS_550)]

        downstream_total = loads[BUS_330] + loads[BUS_440] + loads[BUS_550]

        gen_550 = max(0.0, loads[BUS_550] - limit_330_550)
        remaining_local_need = max(0.0, downstream_total - limit_205_330 - gen_550)
        gen_440 = min(pmax[BUS_440], remaining_local_need)
        gen_550 += max(0.0, downstream_total - limit_205_330 - gen_440 - gen_550)

        flow_330_550 = loads[BUS_550] - gen_550
        flow_330_440 = loads[BUS_440] - gen_440
        flow_205_330 = downstream_total - gen_440 - gen_550

        gen_101 = min(pmax[BUS_101], limit_101_205, loads[BUS_205] + flow_205_330)
        gen_205 = loads[BUS_205] + flow_205_330 - gen_101
        flow_101_205 = gen_101

        dispatch = {
            BUS_101: gen_101,
            BUS_205: gen_205,
            BUS_440: gen_440,
            BUS_550: gen_550,
        }

        reserve_headroom = sum(
            min(reserve_capacity[bus], pmax[bus] - dispatch[bus])
            for bus in dispatch
        )
        assert reserve_headroom + 1e-9 >= reserve_requirement
        assert gen_205 <= pmax[BUS_205] + 1e-9
        assert abs(flow_101_205) <= limit_101_205 + 1e-9
        assert abs(flow_205_330) <= limit_205_330 + 1e-9
        assert abs(flow_330_440) <= limit_330_440 + 1e-9
        assert abs(flow_330_550) <= limit_330_550 + 1e-9

        line_101_205_binding = abs(flow_101_205) / limit_101_205 * 100.0 >= binding_threshold - 1e-9
        line_205_330_binding = abs(flow_205_330) / limit_205_330 * 100.0 >= binding_threshold - 1e-9
        line_330_550_binding = abs(flow_330_550) / limit_330_550 * 100.0 >= binding_threshold - 1e-9

        downstream_marginal = gen_cost[BUS_440] if gen_440 < pmax[BUS_440] - 1e-9 else gen_cost[BUS_550]
        lmp_205 = gen_cost[BUS_205] if line_101_205_binding else gen_cost[BUS_101]
        lmp_330 = downstream_marginal if line_205_330_binding else lmp_205
        lmp_440 = lmp_330
        lmp_550 = gen_cost[BUS_550] if line_330_550_binding or downstream_marginal == gen_cost[BUS_550] else lmp_330

        lmp_map = {
            BUS_101: round2(gen_cost[BUS_101]),
            BUS_205: round2(lmp_205),
            BUS_330: round2(lmp_330),
            BUS_440: round2(lmp_440),
            BUS_550: round2(lmp_550),
        }

        flows = {
            (BUS_101, BUS_205): flow_101_205,
            (BUS_205, BUS_330): flow_205_330,
            (BUS_330, BUS_440): flow_330_440,
            (BUS_330, BUS_550): flow_330_550,
        }
        binding_lines = []
        for row in network["branch"]:
            from_bus = int(row[0])
            to_bus = int(row[1])
            limit = float(row[5])
            flow = float(flows[(from_bus, to_bus)])
            loading_pct = abs(flow) / limit * 100.0
            if loading_pct + 1e-9 >= binding_threshold:
                binding_lines.append(
                    {
                        "from": from_bus,
                        "to": to_bus,
                        "flow_MW": round2(flow),
                        "limit_MW": round2(limit),
                        "loading_pct": round2(loading_pct),
                    }
                )

        total_cost = sum(dispatch[bus] * gen_cost[bus] for bus in dispatch)
        return {
            "scenario_id": scenario_id,
            "total_cost_dollars_per_hour": round2(total_cost),
            "reserve_mcp_dollars_per_MWh": 0.0,
            "lmp_by_bus": [
                {"bus": bus, "lmp_dollars_per_MWh": lmp_map[bus]}
                for bus in bus_numbers
            ],
            "binding_lines": binding_lines,
        }

    base_case = solve_case("base_case")
    base_lmp = {item["bus"]: item["lmp_dollars_per_MWh"] for item in base_case["lmp_by_bus"]}
    base_binding = {(item["from"], item["to"]) for item in base_case["binding_lines"]}

    candidate_assessments = []
    for candidate in config["candidate_buses"]:
        bus = int(candidate["interconnection_bus"])
        scenario_id = f"candidate_{candidate['candidate_id']}"
        case = solve_case(scenario_id, extra_bus=bus)
        lmp_map = {item["bus"]: item["lmp_dollars_per_MWh"] for item in case["lmp_by_bus"]}

        abs_deltas = [abs(lmp_map[bus_num] - base_lmp[bus_num]) for bus_num in bus_numbers]
        affected_bus_count = sum(
            1
            for delta in abs_deltas
            if delta + 1e-9 >= price_diffusion_threshold
        )

        new_binding_lines = [
            line
            for line in case["binding_lines"]
            if (line["from"], line["to"]) not in base_binding
        ]

        candidate_assessments.append(
            {
                "scenario_id": scenario_id,
                "candidate_id": candidate["candidate_id"],
                "interconnection_bus": bus,
                "added_load_MW": round2(added_load_mw),
                "total_cost_dollars_per_hour": case["total_cost_dollars_per_hour"],
                "incremental_cost_dollars_per_hour": round2(
                    case["total_cost_dollars_per_hour"] - base_case["total_cost_dollars_per_hour"]
                ),
                "reserve_mcp_dollars_per_MWh": case["reserve_mcp_dollars_per_MWh"],
                "target_bus_lmp_dollars_per_MWh": lmp_map[bus],
                "lmp_by_bus": case["lmp_by_bus"],
                "price_diffusion_summary": {
                    "affected_bus_count": affected_bus_count,
                    "max_abs_lmp_change_dollars_per_MWh": round2(max(abs_deltas)),
                    "average_abs_lmp_change_dollars_per_MWh": round2(sum(abs_deltas) / len(abs_deltas)),
                },
                "new_binding_lines": new_binding_lines,
            }
        )

    ranking_source = sorted(
        candidate_assessments,
        key=lambda item: (
            item["incremental_cost_dollars_per_hour"],
            item["target_bus_lmp_dollars_per_MWh"],
            item["price_diffusion_summary"]["affected_bus_count"],
            len(item["new_binding_lines"]),
            item["interconnection_bus"],
        ),
    )

    ranking = []
    for idx, item in enumerate(ranking_source, start=1):
        ranking.append(
            {
                "rank": idx,
                "candidate_id": item["candidate_id"],
                "interconnection_bus": item["interconnection_bus"],
                "incremental_cost_dollars_per_hour": item["incremental_cost_dollars_per_hour"],
                "target_bus_lmp_dollars_per_MWh": item["target_bus_lmp_dollars_per_MWh"],
                "affected_bus_count": item["price_diffusion_summary"]["affected_bus_count"],
                "new_binding_lines_count": len(item["new_binding_lines"]),
            }
        )

    selected = ranking_source[0]
    runner_up = ranking_source[1]

    return {
        "base_case": base_case,
        "candidate_assessments": candidate_assessments,
        "recommendation": {
            "selected_candidate_id": selected["candidate_id"],
            "selected_interconnection_bus": selected["interconnection_bus"],
            "ranking": ranking,
            "decision_basis": {
                "selection_rule": "lowest incremental cost, then lower target-bus LMP, then fewer affected buses, then fewer newly binding lines, then lower bus number",
                "runner_up_candidate_id": runner_up["candidate_id"],
                "incremental_cost_advantage_dollars_per_hour": round2(
                    runner_up["incremental_cost_dollars_per_hour"] - selected["incremental_cost_dollars_per_hour"]
                ),
                "target_bus_lmp_advantage_dollars_per_MWh": round2(
                    runner_up["target_bus_lmp_dollars_per_MWh"] - selected["target_bus_lmp_dollars_per_MWh"]
                ),
            },
        },
    }


class TestSchema:
    def test_top_level_keys(self, output):
        assert set(output) == {"base_case", "candidate_assessments", "recommendation"}

    def test_base_case_shape(self, output, network):
        expected_buses = sorted(int(row[0]) for row in network["bus"])
        base_case = output["base_case"]
        assert base_case["scenario_id"] == "base_case"
        assert [item["bus"] for item in base_case["lmp_by_bus"]] == expected_buses
        assert isinstance(base_case["binding_lines"], list)

    def test_candidate_case_order_and_shape(self, output, config, network):
        expected_ids = [item["candidate_id"] for item in config["candidate_buses"]]
        expected_buses = sorted(int(row[0]) for row in network["bus"])
        actual_ids = [item["candidate_id"] for item in output["candidate_assessments"]]
        assert actual_ids == expected_ids
        for case in output["candidate_assessments"]:
            assert [item["bus"] for item in case["lmp_by_bus"]] == expected_buses
            assert isinstance(case["new_binding_lines"], list)
            assert set(case["price_diffusion_summary"]) == {
                "affected_bus_count",
                "max_abs_lmp_change_dollars_per_MWh",
                "average_abs_lmp_change_dollars_per_MWh",
            }

    def test_recommendation_shape(self, output, config):
        ranking = output["recommendation"]["ranking"]
        assert len(ranking) == len(config["candidate_buses"])
        assert [item["rank"] for item in ranking] == list(range(1, len(ranking) + 1))


class TestValues:
    def test_exact_output(self, output, reference):
        assert output == reference

    def test_selected_candidate(self, output):
        assert output["recommendation"]["selected_candidate_id"] == "airport_hub"
        assert output["recommendation"]["selected_interconnection_bus"] == 205

    def test_ranking_order(self, output):
        assert [item["candidate_id"] for item in output["recommendation"]["ranking"]] == [
            "airport_hub",
            "industrial_loop",
            "metro_spur",
            "coastal_landing",
        ]

    def test_base_binding_line(self, output):
        assert output["base_case"]["binding_lines"] == [
            {
                "from": 205,
                "to": 330,
                "flow_MW": 110.0,
                "limit_MW": 110.0,
                "loading_pct": 100.0,
            }
        ]
