#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import math
from pathlib import Path


def resolve_input() -> Path:
    for candidate in (
        Path("/root/peak_hour_snapshot.json"),
        Path("environment/peak_hour_snapshot.json"),
    ):
        try:
            exists = candidate.exists()
        except PermissionError:
            exists = False
        if exists:
            return candidate
    raise FileNotFoundError("peak_hour_snapshot.json not found")


def round6(value: float) -> float:
    return round(float(value), 6)


def branch_flow(branch: dict, voltage_by_bus: dict, base_mva: float) -> dict:
    from_bus = branch["from_bus"]
    to_bus = branch["to_bus"]
    vm_i, va_i_deg = voltage_by_bus[from_bus]
    vm_j, va_j_deg = voltage_by_bus[to_bus]

    tap = branch["tap"] if abs(branch["tap"]) >= 1e-12 else 1.0
    shift = math.radians(branch["shift_deg"])
    r = branch["r_pu"]
    x = branch["x_pu"]
    bc = branch["b_pu"]

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
    overload = max(0.0, worst - branch["rateA_MVA"])

    return {
        "id": branch["id"],
        "from_bus": from_bus,
        "to_bus": to_bus,
        "p_from_MW": p_from,
        "q_from_MVAr": q_from,
        "s_from_MVA": s_from,
        "p_to_MW": p_to,
        "q_to_MVAr": q_to,
        "s_to_MVA": s_to,
        "limit_MVA": branch["rateA_MVA"],
        "loading_pct": 0.0 if branch["rateA_MVA"] <= 0 else 100.0 * worst / branch["rateA_MVA"],
        "overload_MVA": overload,
        "real_loss_MW": p_from + p_to,
    }


input_path = resolve_input()
output_path = Path("/root/feasibility_audit.json") if str(input_path).startswith("/root/") else Path("feasibility_audit.json")
snapshot = json.loads(input_path.read_text())
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

    entry = {
        "bus": bus_id,
        "vm_pu": round6(vm_pu),
        "va_deg": round6(va_deg),
        "p_generation_MW": round6(generation["p_generation_MW"]),
        "q_generation_MVAr": round6(generation["q_generation_MVAr"]),
        "p_load_MW": round6(float(bus["pd_MW"])),
        "q_load_MVAr": round6(float(bus["qd_MVAr"])),
        "p_branch_out_MW": round6(branch_out["p_branch_out_MW"]),
        "q_branch_out_MVAr": round6(branch_out["q_branch_out_MVAr"]),
        "p_balance_residual_MW": round6(p_residual),
        "q_balance_residual_MVAr": round6(q_residual),
        "voltage_violation_pu": round6(voltage_violation),
    }
    bus_balance.append(entry)

    if voltage_violation > 0.0:
        voltage_violations.append(
            {
                "bus": bus_id,
                "vm_pu": round6(vm_pu),
                "vmin_pu": round6(float(bus["vmin_pu"])),
                "vmax_pu": round6(float(bus["vmax_pu"])),
                "violation_pu": round6(voltage_violation),
            }
        )

for rank, branch in enumerate(branch_results, start=1):
    branch["rank"] = rank
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
        branch[key] = round6(branch[key])
    branch.pop("real_loss_MW")

overloaded_branches = [
    {
        "id": branch["id"],
        "from_bus": branch["from_bus"],
        "to_bus": branch["to_bus"],
        "loading_pct": branch["loading_pct"],
        "overload_MVA": branch["overload_MVA"],
    }
    for branch in branch_results
    if branch["overload_MVA"] > 0.0
]

total_generation_mw = sum(float(gen["pg_MW"]) for gen in snapshot["generators"])
total_generation_mvar = sum(float(gen["qg_MVAr"]) for gen in snapshot["generators"])
total_load_mw = sum(float(bus["pd_MW"]) for bus in snapshot["buses"])
total_load_mvar = sum(float(bus["qd_MVAr"]) for bus in snapshot["buses"])
total_real_losses_mw = total_generation_mw - total_load_mw

audit = {
    "case_id": snapshot["case_id"],
    "summary": {
        "baseMVA": round6(base_mva),
        "total_generation_MW": round6(total_generation_mw),
        "total_generation_MVAr": round6(total_generation_mvar),
        "total_load_MW": round6(total_load_mw),
        "total_load_MVAr": round6(total_load_mvar),
        "total_real_losses_MW": round6(total_real_losses_mw),
        "total_shunt_reactive_injection_MVAr": round6(total_shunt_reactive_injection),
        "worst_branch_loading_pct": round6(branch_results[0]["loading_pct"]),
        "max_p_balance_residual_MW": round6(max_p_residual),
        "max_q_balance_residual_MVAr": round6(max_q_residual),
        "max_voltage_violation_pu": round6(max_voltage_violation),
        "max_branch_overload_MVA": round6(max((branch["overload_MVA"] for branch in branch_results), default=0.0)),
        "overloaded_branch_count": len(overloaded_branches),
    },
    "branch_audit": branch_results,
    "bus_balance": bus_balance,
    "violations": {
        "overloaded_branches": overloaded_branches,
        "voltage_violations": voltage_violations,
    },
}

output_path.write_text(json.dumps(audit, indent=2) + "\n")
PY
