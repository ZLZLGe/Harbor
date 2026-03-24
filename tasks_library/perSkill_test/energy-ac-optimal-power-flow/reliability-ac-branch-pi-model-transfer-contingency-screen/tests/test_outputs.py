import json
import math
from pathlib import Path


TOL = 1e-3


def resolve(path_in_root: str, local_fallback: str) -> Path:
    primary = Path(path_in_root)
    try:
        exists = primary.exists()
    except PermissionError:
        exists = False
    if exists:
        return primary
    return Path(local_fallback)


def load_cases() -> dict:
    path = resolve("/root/contingency_cases.json", "environment/contingency_cases.json")
    return json.loads(path.read_text())


def load_output() -> dict:
    path = resolve("/root/contingency_screen.json", "contingency_screen.json")
    if not path.exists():
        raise AssertionError("contingency_screen.json was not created")
    return json.loads(path.read_text())


def approx_equal(left: float, right: float, tol: float = TOL) -> None:
    assert math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tol), (left, right)


def branch_flow(branch: dict, voltage_by_bus: dict, base_mva: float) -> dict:
    vm_i, va_i_deg = voltage_by_bus[int(branch["from_bus"])]
    vm_j, va_j_deg = voltage_by_bus[int(branch["to_bus"])]
    tap = float(branch["tap"]) if abs(float(branch["tap"])) >= 1e-12 else 1.0
    shift = math.radians(float(branch["shift_deg"]))
    r = float(branch["r_pu"])
    x = float(branch["x_pu"])
    bc = float(branch["b_pu"])

    if abs(r) < 1e-12 and abs(x) < 1e-12:
        g = 0.0
        b = 0.0
    else:
        denom = r * r + x * x
        g = r / denom
        b = -x / denom

    va_i = math.radians(va_i_deg)
    va_j = math.radians(va_j_deg)
    inv_t = 1.0 / tap
    inv_t2 = inv_t * inv_t

    delta_ij = va_i - va_j - shift
    p_from_pu = g * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ij) + b * math.sin(delta_ij)
    )
    q_from_pu = -(b + bc / 2.0) * vm_i * vm_i * inv_t2 - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ij) - b * math.cos(delta_ij)
    )

    delta_ji = va_j - va_i + shift
    p_to_pu = g * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.cos(delta_ji) + b * math.sin(delta_ji)
    )
    q_to_pu = -(b + bc / 2.0) * vm_j * vm_j - vm_i * vm_j * inv_t * (
        g * math.sin(delta_ji) - b * math.cos(delta_ji)
    )

    p_from = p_from_pu * base_mva
    q_from = q_from_pu * base_mva
    p_to = p_to_pu * base_mva
    q_to = q_to_pu * base_mva
    s_from = math.hypot(p_from, q_from)
    s_to = math.hypot(p_to, q_to)
    worst = max(s_from, s_to)
    limit = float(branch["rateA_MVA"])

    return {
        "id": branch["id"],
        "from_bus": int(branch["from_bus"]),
        "to_bus": int(branch["to_bus"]),
        "p_from_MW": p_from,
        "q_from_MVAr": q_from,
        "s_from_MVA": s_from,
        "p_to_MW": p_to,
        "q_to_MVAr": q_to,
        "s_to_MVA": s_to,
        "limit_MVA": limit,
        "loading_pct": 0.0 if limit <= 0.0 else 100.0 * worst / limit,
        "overload_MVA": max(0.0, worst - limit),
    }


def choose_worst_branch(records: list[dict]) -> dict:
    return sorted(records, key=lambda item: (-item["overload_MVA"], -item["loading_pct"], item["id"]))[0]


def expected_report(cases: dict) -> dict:
    base_mva = float(cases["baseMVA"])
    scenario_results = []

    for scenario in cases["scenarios"]:
        voltage_by_bus = {
            int(item["bus"]): (float(item["vm_pu"]), float(item["va_deg"]))
            for item in scenario["bus_voltages"]
        }
        surviving = [
            branch_flow(branch, voltage_by_bus, base_mva)
            for branch in cases["branches"]
            if branch["id"] != scenario["outaged_branch_id"]
        ]
        worst_branch = choose_worst_branch(surviving)
        scenario_results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "outaged_branch_id": scenario["outaged_branch_id"],
                "surviving_branch_count": len(surviving),
                "overloaded_branch_count": sum(1 for item in surviving if item["overload_MVA"] > 0.0),
                "max_loading_pct": worst_branch["loading_pct"],
                "max_overload_MVA": worst_branch["overload_MVA"],
                "worst_branch": worst_branch,
            }
        )

    scenario_results.sort(
        key=lambda item: (-item["max_overload_MVA"], -item["max_loading_pct"], item["scenario_id"])
    )
    for index, item in enumerate(scenario_results, start=1):
        item["severity_rank"] = index

    worst_scenario = scenario_results[0]
    return {
        "study_id": cases["study_id"],
        "summary": {
            "scenario_count": len(scenario_results),
            "scenarios_with_overloads": sum(1 for item in scenario_results if item["overloaded_branch_count"] > 0),
            "most_dangerous_scenario_id": worst_scenario["scenario_id"],
            "most_dangerous_outaged_branch_id": worst_scenario["outaged_branch_id"],
            "overall_worst_branch_id": worst_scenario["worst_branch"]["id"],
            "overall_worst_loading_pct": worst_scenario["max_loading_pct"],
            "overall_worst_overload_MVA": worst_scenario["max_overload_MVA"],
        },
        "scenario_results": scenario_results,
    }


def test_output_schema() -> None:
    output = load_output()
    assert output["study_id"] == "delta-transfer-screen-2031q3"
    assert isinstance(output["summary"], dict)
    assert isinstance(output["scenario_results"], list)
    assert len(output["scenario_results"]) == 4


def test_contingency_screen_values() -> None:
    cases = load_cases()
    output = load_output()
    expected = expected_report(cases)

    assert output["study_id"] == expected["study_id"]

    for key, value in expected["summary"].items():
        if isinstance(value, int):
            assert output["summary"][key] == value
        elif isinstance(value, str):
            assert output["summary"][key] == value
        else:
            approx_equal(output["summary"][key], value)

    for actual, reference in zip(output["scenario_results"], expected["scenario_results"]):
        assert actual["severity_rank"] == reference["severity_rank"]
        assert actual["scenario_id"] == reference["scenario_id"]
        assert actual["outaged_branch_id"] == reference["outaged_branch_id"]
        assert actual["surviving_branch_count"] == reference["surviving_branch_count"]
        assert actual["overloaded_branch_count"] == reference["overloaded_branch_count"]
        approx_equal(actual["max_loading_pct"], reference["max_loading_pct"])
        approx_equal(actual["max_overload_MVA"], reference["max_overload_MVA"])

        actual_branch = actual["worst_branch"]
        reference_branch = reference["worst_branch"]
        assert actual_branch["id"] == reference_branch["id"]
        assert actual_branch["from_bus"] == reference_branch["from_bus"]
        assert actual_branch["to_bus"] == reference_branch["to_bus"]
        for key in (
            "p_from_MW",
            "q_from_MVAr",
            "s_from_MVA",
            "p_to_MW",
            "q_to_MVAr",
            "s_to_MVA",
            "limit_MVA",
            "loading_pct",
            "overload_MVA",
        ):
            approx_equal(actual_branch[key], reference_branch[key])


def test_sorted_by_severity() -> None:
    output = load_output()
    pairs = [
        (item["max_overload_MVA"], item["max_loading_pct"], item["scenario_id"])
        for item in output["scenario_results"]
    ]
    expected_pairs = sorted(pairs, key=lambda item: (-item[0], -item[1], item[2]))
    assert pairs == expected_pairs
