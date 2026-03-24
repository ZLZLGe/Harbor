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


def load_snapshot() -> dict:
    path = resolve("/root/peak_hour_snapshot.json", "environment/peak_hour_snapshot.json")
    return json.loads(path.read_text())


def load_output() -> dict:
    path = resolve("/root/feasibility_audit.json", "feasibility_audit.json")
    if not path.exists():
        raise AssertionError("feasibility_audit.json was not created")
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
    overload = max(0.0, worst - float(branch["rateA_MVA"]))

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
        "limit_MVA": float(branch["rateA_MVA"]),
        "loading_pct": 0.0 if float(branch["rateA_MVA"]) <= 0 else 100.0 * worst / float(branch["rateA_MVA"]),
        "overload_MVA": overload,
    }


def expected_audit(snapshot: dict) -> dict:
    base_mva = float(snapshot["baseMVA"])
    voltage_by_bus = {
        int(item["bus"]): (float(item["vm_pu"]), float(item["va_deg"]))
        for item in snapshot["snapshot"]["bus_voltages"]
    }

    gen_by_bus = {}
    for gen in snapshot["generators"]:
        bus = int(gen["bus"])
        totals = gen_by_bus.setdefault(bus, {"p_generation_MW": 0.0, "q_generation_MVAr": 0.0})
        totals["p_generation_MW"] += float(gen["pg_MW"])
        totals["q_generation_MVAr"] += float(gen["qg_MVAr"])

    branch_results = []
    branch_out_by_bus = {
        int(bus["id"]): {"p_branch_out_MW": 0.0, "q_branch_out_MVAr": 0.0}
        for bus in snapshot["buses"]
    }
    for branch in snapshot["branches"]:
        record = branch_flow(branch, voltage_by_bus, base_mva)
        branch_results.append(record)
        branch_out_by_bus[record["from_bus"]]["p_branch_out_MW"] += record["p_from_MW"]
        branch_out_by_bus[record["from_bus"]]["q_branch_out_MVAr"] += record["q_from_MVAr"]
        branch_out_by_bus[record["to_bus"]]["p_branch_out_MW"] += record["p_to_MW"]
        branch_out_by_bus[record["to_bus"]]["q_branch_out_MVAr"] += record["q_to_MVAr"]

    branch_results.sort(key=lambda item: (-item["loading_pct"], item["id"]))
    for rank, record in enumerate(branch_results, start=1):
        record["rank"] = rank

    bus_balance = []
    voltage_violations = []
    total_shunt_reactive_injection = 0.0
    max_p_residual = 0.0
    max_q_residual = 0.0
    max_voltage_violation = 0.0

    for bus in sorted(snapshot["buses"], key=lambda item: int(item["id"])):
        bus_id = int(bus["id"])
        vm_pu, va_deg = voltage_by_bus[bus_id]
        generation = gen_by_bus.get(bus_id, {"p_generation_MW": 0.0, "q_generation_MVAr": 0.0})
        branch_out = branch_out_by_bus[bus_id]
        shunt_p = float(bus["gs_MW_at_1pu"]) * vm_pu * vm_pu
        shunt_q = float(bus["bs_MVAr_at_1pu"]) * vm_pu * vm_pu
        total_shunt_reactive_injection += shunt_q

        p_residual = generation["p_generation_MW"] - float(bus["pd_MW"]) - shunt_p - branch_out["p_branch_out_MW"]
        q_residual = generation["q_generation_MVAr"] - float(bus["qd_MVAr"]) + shunt_q - branch_out["q_branch_out_MVAr"]
        voltage_violation = max(float(bus["vmin_pu"]) - vm_pu, 0.0, vm_pu - float(bus["vmax_pu"]))

        max_p_residual = max(max_p_residual, abs(p_residual))
        max_q_residual = max(max_q_residual, abs(q_residual))
        max_voltage_violation = max(max_voltage_violation, voltage_violation)

        bus_balance.append(
            {
                "bus": bus_id,
                "vm_pu": vm_pu,
                "va_deg": va_deg,
                "p_generation_MW": generation["p_generation_MW"],
                "q_generation_MVAr": generation["q_generation_MVAr"],
                "p_load_MW": float(bus["pd_MW"]),
                "q_load_MVAr": float(bus["qd_MVAr"]),
                "p_branch_out_MW": branch_out["p_branch_out_MW"],
                "q_branch_out_MVAr": branch_out["q_branch_out_MVAr"],
                "p_balance_residual_MW": p_residual,
                "q_balance_residual_MVAr": q_residual,
                "voltage_violation_pu": voltage_violation,
            }
        )

        if voltage_violation > 0.0:
            voltage_violations.append(
                {
                    "bus": bus_id,
                    "vm_pu": vm_pu,
                    "vmin_pu": float(bus["vmin_pu"]),
                    "vmax_pu": float(bus["vmax_pu"]),
                    "violation_pu": voltage_violation,
                }
            )

    overloaded = [
        {
            "id": record["id"],
            "from_bus": record["from_bus"],
            "to_bus": record["to_bus"],
            "loading_pct": record["loading_pct"],
            "overload_MVA": record["overload_MVA"],
        }
        for record in branch_results
        if record["overload_MVA"] > 0.0
    ]

    total_generation_mw = sum(float(gen["pg_MW"]) for gen in snapshot["generators"])
    total_generation_mvar = sum(float(gen["qg_MVAr"]) for gen in snapshot["generators"])
    total_load_mw = sum(float(bus["pd_MW"]) for bus in snapshot["buses"])
    total_load_mvar = sum(float(bus["qd_MVAr"]) for bus in snapshot["buses"])

    return {
        "case_id": snapshot["case_id"],
        "summary": {
            "baseMVA": base_mva,
            "total_generation_MW": total_generation_mw,
            "total_generation_MVAr": total_generation_mvar,
            "total_load_MW": total_load_mw,
            "total_load_MVAr": total_load_mvar,
            "total_real_losses_MW": total_generation_mw - total_load_mw,
            "total_shunt_reactive_injection_MVAr": total_shunt_reactive_injection,
            "worst_branch_loading_pct": branch_results[0]["loading_pct"],
            "max_p_balance_residual_MW": max_p_residual,
            "max_q_balance_residual_MVAr": max_q_residual,
            "max_voltage_violation_pu": max_voltage_violation,
            "max_branch_overload_MVA": max((record["overload_MVA"] for record in branch_results), default=0.0),
            "overloaded_branch_count": len(overloaded),
        },
        "branch_audit": branch_results,
        "bus_balance": bus_balance,
        "violations": {
            "overloaded_branches": overloaded,
            "voltage_violations": voltage_violations,
        },
    }


def test_output_schema() -> None:
    output = load_output()
    assert output["case_id"] == "iso-peak-hour-2030-local"
    assert isinstance(output["summary"], dict)
    assert isinstance(output["branch_audit"], list)
    assert isinstance(output["bus_balance"], list)
    assert isinstance(output["violations"], dict)
    assert len(output["branch_audit"]) == 6
    assert len(output["bus_balance"]) == 5


def test_numeric_audit_values() -> None:
    snapshot = load_snapshot()
    output = load_output()
    expected = expected_audit(snapshot)

    assert output["case_id"] == expected["case_id"]

    for key, value in expected["summary"].items():
        if isinstance(value, int):
            assert output["summary"][key] == value
        else:
            approx_equal(output["summary"][key], value)

    for actual, reference in zip(output["branch_audit"], expected["branch_audit"]):
        assert actual["rank"] == reference["rank"]
        assert actual["id"] == reference["id"]
        assert actual["from_bus"] == reference["from_bus"]
        assert actual["to_bus"] == reference["to_bus"]
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
            approx_equal(actual[key], reference[key])

    for actual, reference in zip(output["bus_balance"], expected["bus_balance"]):
        assert actual["bus"] == reference["bus"]
        for key in (
            "vm_pu",
            "va_deg",
            "p_generation_MW",
            "q_generation_MVAr",
            "p_load_MW",
            "q_load_MVAr",
            "p_branch_out_MW",
            "q_branch_out_MVAr",
            "p_balance_residual_MW",
            "q_balance_residual_MVAr",
            "voltage_violation_pu",
        ):
            approx_equal(actual[key], reference[key])

    actual_overloaded = output["violations"]["overloaded_branches"]
    expected_overloaded = expected["violations"]["overloaded_branches"]
    assert len(actual_overloaded) == len(expected_overloaded)
    for actual, reference in zip(actual_overloaded, expected_overloaded):
        assert actual["id"] == reference["id"]
        assert actual["from_bus"] == reference["from_bus"]
        assert actual["to_bus"] == reference["to_bus"]
        approx_equal(actual["loading_pct"], reference["loading_pct"])
        approx_equal(actual["overload_MVA"], reference["overload_MVA"])

    assert output["violations"]["voltage_violations"] == expected["violations"]["voltage_violations"]
