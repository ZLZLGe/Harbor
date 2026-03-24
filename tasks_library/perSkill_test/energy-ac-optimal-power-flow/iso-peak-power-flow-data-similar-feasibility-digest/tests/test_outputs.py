import json
import math
import os
from pathlib import Path


TASK_DIR = Path.cwd()
if (TASK_DIR / "environment").exists():
    LOCAL_ENV = TASK_DIR / "environment"
else:
    LOCAL_ENV = Path(__file__).resolve().parent.parent / "environment"


def resolve_path(env_var: str, root_name: str, local_name: str) -> Path:
    override = os.environ.get(env_var)
    if override:
        return Path(override)
    root_path = Path("/root") / root_name
    try:
        root_exists = root_path.exists()
    except PermissionError:
        root_exists = False
    if root_exists:
        return root_path
    return LOCAL_ENV / local_name


def resolve_output() -> Path:
    override = os.environ.get("REPORT_OUTPUT")
    if override:
        return Path(override)
    root_path = Path("/root/operations_feasibility_report.json")
    try:
        root_exists = root_path.exists()
    except PermissionError:
        root_exists = False
    if root_exists:
        return root_path
    return TASK_DIR / "operations_feasibility_report.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def branch_flow_values(branch_row, vm_from, va_from, vm_to, va_to, base_mva):
    r = float(branch_row[2])
    x = float(branch_row[3])
    bc = float(branch_row[4])
    tap = float(branch_row[8]) if abs(float(branch_row[8])) >= 1e-12 else 1.0
    shift = math.radians(float(branch_row[9]))

    if abs(r) < 1e-12 and abs(x) < 1e-12:
        g = 0.0
        b = 0.0
    else:
        denom = r * r + x * x
        g = r / denom
        b = -x / denom

    inv_t = 1.0 / tap
    inv_t2 = inv_t * inv_t

    delta_ij = va_from - va_to - shift
    p_ij = g * vm_from * vm_from * inv_t2 - vm_from * vm_to * inv_t * (
        g * math.cos(delta_ij) + b * math.sin(delta_ij)
    )
    q_ij = -(b + bc / 2.0) * vm_from * vm_from * inv_t2 - vm_from * vm_to * inv_t * (
        g * math.sin(delta_ij) - b * math.cos(delta_ij)
    )

    delta_ji = va_to - va_from + shift
    p_ji = g * vm_to * vm_to - vm_from * vm_to * inv_t * (
        g * math.cos(delta_ji) + b * math.sin(delta_ji)
    )
    q_ji = -(b + bc / 2.0) * vm_to * vm_to - vm_from * vm_to * inv_t * (
        g * math.sin(delta_ji) - b * math.cos(delta_ji)
    )

    return {
        "p_ij_MW": p_ij * base_mva,
        "q_ij_MVAr": q_ij * base_mva,
        "p_ji_MW": p_ji * base_mva,
        "q_ji_MVAr": q_ji * base_mva,
    }


def assert_close(actual, expected, tol=1e-6):
    if abs(actual - expected) > tol:
        raise AssertionError(f"expected {expected}, got {actual}")


network = load_json(resolve_path("NETWORK_FILE", "network.json", "network.json"))
candidate = load_json(
    resolve_path("CANDIDATE_FILE", "candidate_operating_point.json", "candidate_operating_point.json")
)
report = load_json(resolve_output())

bus_ids = [int(row[0]) for row in network["bus"]]
if all(curr + 1 == nxt for curr, nxt in zip(bus_ids, bus_ids[1:])):
    raise AssertionError("network bus ids should be non-contiguous in this derived task")

required_top_keys = {"summary", "reference_bus_check", "most_loaded_branches", "feasibility_metrics"}
if set(report.keys()) != required_top_keys:
    raise AssertionError(f"unexpected top-level keys: {sorted(report.keys())}")

base_mva = float(network["baseMVA"])
bus_rows = network["bus"]
gen_rows = network["gen"]
branch_rows = network["branch"]
bus_id_to_idx = {int(row[0]): idx for idx, row in enumerate(bus_rows)}

vm = [0.0] * len(bus_rows)
va = [0.0] * len(bus_rows)
for row in candidate["buses"]:
    idx = bus_id_to_idx[int(row["id"])]
    vm[idx] = float(row["vm_pu"])
    va[idx] = math.radians(float(row["va_deg"]))

pg = [0.0] * len(gen_rows)
qg = [0.0] * len(gen_rows)
for row in candidate["generators"]:
    idx = int(row["id"]) - 1
    pg[idx] = float(row["pg_MW"])
    qg[idx] = float(row["qg_MVAr"])

gens_at_bus = {}
for idx, row in enumerate(gen_rows):
    gens_at_bus.setdefault(int(row[0]), []).append(idx)

active_outflows = [0.0] * len(bus_rows)
reactive_outflows = [0.0] * len(bus_rows)
branch_records = []
for row in branch_rows:
    if int(row[10]) != 1:
        continue
    from_bus = int(row[0])
    to_bus = int(row[1])
    from_idx = bus_id_to_idx[from_bus]
    to_idx = bus_id_to_idx[to_bus]

    flows = branch_flow_values(row, vm[from_idx], va[from_idx], vm[to_idx], va[to_idx], base_mva)
    active_outflows[from_idx] += flows["p_ij_MW"]
    reactive_outflows[from_idx] += flows["q_ij_MVAr"]
    active_outflows[to_idx] += flows["p_ji_MW"]
    reactive_outflows[to_idx] += flows["q_ji_MVAr"]

    limit = float(row[5])
    if limit <= 0:
        continue

    flow_from = math.hypot(flows["p_ij_MW"], flows["q_ij_MVAr"])
    flow_to = math.hypot(flows["p_ji_MW"], flows["q_ji_MVAr"])
    max_flow = max(flow_from, flow_to)
    branch_records.append(
        {
            "from_bus": from_bus,
            "to_bus": to_bus,
            "loading_pct": max_flow / limit * 100.0,
            "flow_from_MVA": flow_from,
            "flow_to_MVA": flow_to,
            "limit_MVA": limit,
            "overload_MVA": max(0.0, max_flow - limit),
        }
    )

branch_records.sort(key=lambda item: (-item["loading_pct"], item["from_bus"], item["to_bus"]))

voltage_violations = []
p_mismatches = []
q_mismatches = []
for idx, row in enumerate(bus_rows):
    bus_id = int(row[0])
    p_gen = sum(pg[gen_idx] for gen_idx in gens_at_bus.get(bus_id, []) if int(gen_rows[gen_idx][7]) == 1)
    q_gen = sum(qg[gen_idx] for gen_idx in gens_at_bus.get(bus_id, []) if int(gen_rows[gen_idx][7]) == 1)

    p_mismatch = p_gen - float(row[2]) - float(row[4]) * (vm[idx] ** 2) - active_outflows[idx]
    q_mismatch = q_gen - float(row[3]) + float(row[5]) * (vm[idx] ** 2) - reactive_outflows[idx]
    p_mismatches.append({"value": abs(p_mismatch), "bus": bus_id})
    q_mismatches.append({"value": abs(q_mismatch), "bus": bus_id})

    violation = max(0.0, vm[idx] - float(row[11]), float(row[12]) - vm[idx])
    if violation > 0:
        voltage_violations.append({"value": violation, "bus": bus_id})

generator_p_violations = []
generator_q_violations = []
for idx, row in enumerate(gen_rows):
    if int(row[7]) != 1:
        continue
    p_violation = max(0.0, pg[idx] - float(row[8]), float(row[9]) - pg[idx])
    q_violation = max(0.0, qg[idx] - float(row[3]), float(row[4]) - qg[idx])
    if p_violation > 0:
        generator_p_violations.append({"value": p_violation, "generator_id": idx + 1})
    if q_violation > 0:
        generator_q_violations.append({"value": q_violation, "generator_id": idx + 1})

branch_overloads = [
    {"value": row["overload_MVA"], "from_bus": row["from_bus"], "to_bus": row["to_bus"]}
    for row in branch_records
    if row["overload_MVA"] > 0
]

worst_p = max(p_mismatches, key=lambda item: (item["value"], -item["bus"]))
worst_q = max(q_mismatches, key=lambda item: (item["value"], -item["bus"]))
worst_v = max(voltage_violations, key=lambda item: (item["value"], -item["bus"]))
worst_gp = max(generator_p_violations, key=lambda item: (item["value"], -item["generator_id"]))
worst_gq = max(generator_q_violations, key=lambda item: (item["value"], -item["generator_id"]))
worst_bo = max(branch_overloads, key=lambda item: (item["value"], -item["from_bus"], -item["to_bus"]))

expected_summary = {
    "total_load_MW": sum(float(row[2]) for row in bus_rows),
    "total_load_MVAr": sum(float(row[3]) for row in bus_rows),
    "total_generation_MW": sum(pg[idx] for idx, row in enumerate(gen_rows) if int(row[7]) == 1),
    "total_generation_MVAr": sum(qg[idx] for idx, row in enumerate(gen_rows) if int(row[7]) == 1),
}
expected_summary["total_losses_MW"] = expected_summary["total_generation_MW"] - expected_summary["total_load_MW"]

for key, expected in expected_summary.items():
    assert_close(float(report["summary"][key]), expected)

reference_bus = next(int(row[0]) for row in bus_rows if int(row[1]) == 3)
reference_angle_deg = next(
    float(row["va_deg"]) for row in candidate["buses"] if int(row["id"]) == reference_bus
)
reference = report["reference_bus_check"]
if int(reference["reference_bus"]) != reference_bus:
    raise AssertionError("reference bus mismatch")
assert_close(float(reference["angle_deg"]), reference_angle_deg)
assert_close(float(reference["target_angle_deg"]), 0.0)
assert_close(float(reference["tolerance_deg"]), 0.1)
assert_close(float(reference["abs_deviation_deg"]), abs(reference_angle_deg))
if bool(reference["within_tolerance"]) != (abs(reference_angle_deg) <= 0.1):
    raise AssertionError("reference angle tolerance flag mismatch")

expected_top = branch_records[:10]
actual_top = report["most_loaded_branches"]
if len(actual_top) != 10:
    raise AssertionError(f"expected 10 loaded branches, got {len(actual_top)}")
for actual, expected in zip(actual_top, expected_top):
    if int(actual["from_bus"]) != expected["from_bus"] or int(actual["to_bus"]) != expected["to_bus"]:
        raise AssertionError("most_loaded_branches ordering mismatch")
    for key in ["loading_pct", "flow_from_MVA", "flow_to_MVA", "limit_MVA", "overload_MVA"]:
        assert_close(float(actual[key]), expected[key])

metrics = report["feasibility_metrics"]
assert_close(float(metrics["max_p_mismatch_MW"]), worst_p["value"])
if int(metrics["worst_p_mismatch_bus"]) != worst_p["bus"]:
    raise AssertionError("worst_p_mismatch_bus mismatch")
assert_close(float(metrics["max_q_mismatch_MVAr"]), worst_q["value"])
if int(metrics["worst_q_mismatch_bus"]) != worst_q["bus"]:
    raise AssertionError("worst_q_mismatch_bus mismatch")

voltage = metrics["voltage_violations"]
if int(voltage["count"]) != len(voltage_violations):
    raise AssertionError("voltage violation count mismatch")
assert_close(float(voltage["max_violation_pu"]), worst_v["value"])
if int(voltage["worst_bus"]) != worst_v["bus"]:
    raise AssertionError("worst voltage bus mismatch")

generator_p = metrics["generator_p_violations"]
if int(generator_p["count"]) != len(generator_p_violations):
    raise AssertionError("generator_p violation count mismatch")
assert_close(float(generator_p["max_violation_MW"]), worst_gp["value"])
if int(generator_p["worst_generator_id"]) != worst_gp["generator_id"]:
    raise AssertionError("worst generator P mismatch")

generator_q = metrics["generator_q_violations"]
if int(generator_q["count"]) != len(generator_q_violations):
    raise AssertionError("generator_q violation count mismatch")
assert_close(float(generator_q["max_violation_MVAr"]), worst_gq["value"])
if int(generator_q["worst_generator_id"]) != worst_gq["generator_id"]:
    raise AssertionError("worst generator Q mismatch")

branch_overload = metrics["branch_overloads"]
if int(branch_overload["count"]) != len(branch_overloads):
    raise AssertionError("branch overload count mismatch")
assert_close(float(branch_overload["max_overload_MVA"]), worst_bo["value"])
if int(branch_overload["worst_branch"]["from_bus"]) != worst_bo["from_bus"]:
    raise AssertionError("worst overloaded branch from-bus mismatch")
if int(branch_overload["worst_branch"]["to_bus"]) != worst_bo["to_bus"]:
    raise AssertionError("worst overloaded branch to-bus mismatch")
