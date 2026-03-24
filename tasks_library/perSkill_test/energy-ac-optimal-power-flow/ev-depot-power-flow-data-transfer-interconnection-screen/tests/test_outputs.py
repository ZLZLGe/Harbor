import json
import os
from collections import defaultdict
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
    root_path = Path("/root/ev_depot_screen.json")
    try:
        root_exists = root_path.exists()
    except PermissionError:
        root_exists = False
    if root_exists:
        return root_path
    return TASK_DIR / "ev_depot_screen.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def positive(value: float) -> float:
    value = float(value)
    return value if value > 0 else 0.0


def normalize_high(value: float, min_value: float, max_value: float) -> float:
    if abs(max_value - min_value) < 1e-12:
        return 1.0
    return (value - min_value) / (max_value - min_value)


def normalize_low(value: float, min_value: float, max_value: float) -> float:
    if abs(max_value - min_value) < 1e-12:
        return 1.0
    return (max_value - value) / (max_value - min_value)


def r4(value: float) -> float:
    return round(float(value), 4)


def compare(actual, expected, path="root"):
    if isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            raise AssertionError(f"{path}: key mismatch {sorted(actual.keys())} != {sorted(expected.keys())}")
        for key in expected:
            compare(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if len(actual) != len(expected):
            raise AssertionError(f"{path}: length mismatch {len(actual)} != {len(expected)}")
        for idx, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            compare(actual_item, expected_item, f"{path}[{idx}]")
        return
    if isinstance(expected, float):
        if abs(float(actual) - expected) > 1e-6:
            raise AssertionError(f"{path}: expected {expected}, got {actual}")
        return
    if actual != expected:
        raise AssertionError(f"{path}: expected {expected}, got {actual}")


network = load_json(resolve_path("NETWORK_FILE", "network.json", "network.json"))
config = load_json(resolve_path("CANDIDATE_FILE", "candidate_buses.json", "candidate_buses.json"))
report = load_json(resolve_output())

required_top_keys = {"screening_context", "status_summary", "ranked_candidates"}
if set(report.keys()) != required_top_keys:
    raise AssertionError(f"unexpected top-level keys: {sorted(report.keys())}")

bus_ids_in_order = [int(row[0]) for row in network["bus"]]
if bus_ids_in_order == sorted(bus_ids_in_order):
    raise AssertionError("bus rows should be intentionally unsorted in this transfer task")

bus_by_id = {int(row[0]): row for row in network["bus"]}
gen_rows_by_bus = defaultdict(list)
for row in network["gen"]:
    gen_rows_by_bus[int(row[0])].append(row)

active_branch_rows_by_bus = defaultdict(list)
neighbor_buses_by_bus = defaultdict(set)
for row in network["branch"]:
    if int(row[10]) != 1:
        continue
    from_bus = int(row[0])
    to_bus = int(row[1])
    active_branch_rows_by_bus[from_bus].append(row)
    active_branch_rows_by_bus[to_bus].append(row)
    neighbor_buses_by_bus[from_bus].add(to_bus)
    neighbor_buses_by_bus[to_bus].add(from_bus)

records = []
preferred_voltage_kv = float(config["preferred_voltage_kV"])
for item in config["candidate_buses"]:
    bus_id = int(item["bus"])
    row = bus_by_id[bus_id]
    branch_rows_at_bus = active_branch_rows_by_bus[bus_id]
    unique_neighbors = sorted(neighbor_buses_by_bus[bus_id])
    same_bus_generation_margin = sum(
        max(float(gen_row[8]) - float(gen_row[1]), 0.0)
        for gen_row in gen_rows_by_bus.get(bus_id, [])
        if int(gen_row[7]) == 1
    )
    records.append(
        {
            "bus": bus_id,
            "site_code": item["site_code"],
            "base_kV": float(row[9]),
            "existing_load_MW": positive(row[2]),
            "same_bus_generation_margin_MW": same_bus_generation_margin,
            "adjacent_branch_count": len(branch_rows_at_bus),
            "adjacent_branch_capacity_MVA_sum": sum(max(float(branch_row[5]), 0.0) for branch_row in branch_rows_at_bus),
            "max_adjacent_branch_MVA": max(
                (max(float(branch_row[5]), 0.0) for branch_row in branch_rows_at_bus),
                default=0.0,
            ),
            "one_hop_neighbor_count": len(unique_neighbors),
            "one_hop_115kV_plus_neighbor_count": sum(
                1 for neighbor_bus in unique_neighbors if float(bus_by_id[neighbor_bus][9]) >= preferred_voltage_kv
            ),
            "one_hop_generator_bus_count": sum(
                1
                for neighbor_bus in unique_neighbors
                if any(
                    int(gen_row[7]) == 1 and (float(gen_row[8]) - float(gen_row[1])) > 0.0
                    for gen_row in gen_rows_by_bus.get(neighbor_bus, [])
                )
            ),
            "one_hop_total_neighbor_load_MW": sum(
                positive(bus_by_id[neighbor_bus][2]) for neighbor_bus in unique_neighbors
            ),
        }
    )


def bounds(key: str):
    values = [record[key] for record in records]
    return min(values), max(values)


base_kv_min, base_kv_max = bounds("base_kV")
load_min, load_max = bounds("existing_load_MW")
margin_min, margin_max = bounds("same_bus_generation_margin_MW")
capacity_min, capacity_max = bounds("adjacent_branch_capacity_MVA_sum")
neighbor_count_min, neighbor_count_max = bounds("one_hop_neighbor_count")
hv_neighbor_min, hv_neighbor_max = bounds("one_hop_115kV_plus_neighbor_count")
gen_neighbor_min, gen_neighbor_max = bounds("one_hop_generator_bus_count")

ranked = []
for record in records:
    voltage_level = normalize_high(record["base_kV"], base_kv_min, base_kv_max)
    existing_load = normalize_low(record["existing_load_MW"], load_min, load_max)
    same_bus_generation_margin = normalize_high(
        record["same_bus_generation_margin_MW"], margin_min, margin_max
    )
    adjacent_branch_capacity = normalize_high(
        record["adjacent_branch_capacity_MVA_sum"], capacity_min, capacity_max
    )
    one_hop_topology = (
        0.5 * normalize_high(record["one_hop_neighbor_count"], neighbor_count_min, neighbor_count_max)
        + 0.3
        * normalize_high(
            record["one_hop_115kV_plus_neighbor_count"], hv_neighbor_min, hv_neighbor_max
        )
        + 0.2
        * normalize_high(record["one_hop_generator_bus_count"], gen_neighbor_min, gen_neighbor_max)
    )
    score = 100.0 * (
        float(config["weights"]["voltage_level"]) * voltage_level
        + float(config["weights"]["existing_load"]) * existing_load
        + float(config["weights"]["same_bus_generation_margin"]) * same_bus_generation_margin
        + float(config["weights"]["adjacent_branch_capacity"]) * adjacent_branch_capacity
        + float(config["weights"]["one_hop_topology"]) * one_hop_topology
    )

    base_kv = record["base_kV"]
    if (
        base_kv >= float(config["preferred_voltage_kV"])
        and score >= float(config["status_thresholds"]["preferred_min_score"])
    ):
        status = "preferred"
    elif (
        base_kv >= float(config["minimum_voltage_kV"])
        and score >= float(config["status_thresholds"]["conditional_min_score"])
    ):
        status = "conditional"
    else:
        status = "reject"

    ranked.append(
        {
            "bus": record["bus"],
            "site_code": record["site_code"],
            "score": r4(score),
            "status": status,
            "score_breakdown": {
                "voltage_level": r4(voltage_level),
                "existing_load": r4(existing_load),
                "same_bus_generation_margin": r4(same_bus_generation_margin),
                "adjacent_branch_capacity": r4(adjacent_branch_capacity),
                "one_hop_topology": r4(one_hop_topology),
            },
            "screening_flags": {
                "meets_minimum_voltage": base_kv >= float(config["minimum_voltage_kV"]),
                "meets_preferred_voltage": base_kv >= float(config["preferred_voltage_kV"]),
                "has_same_bus_generation_margin": record["same_bus_generation_margin_MW"] > 0.0,
                "strong_branch_capacity_proxy": (
                    record["adjacent_branch_capacity_MVA_sum"]
                    >= float(config["strong_branch_capacity_threshold_MVA"])
                ),
            },
            "summary": {
                "base_kV": r4(record["base_kV"]),
                "existing_load_MW": r4(record["existing_load_MW"]),
                "same_bus_generation_margin_MW": r4(record["same_bus_generation_margin_MW"]),
                "adjacent_branch_count": int(record["adjacent_branch_count"]),
                "adjacent_branch_capacity_MVA_sum": r4(record["adjacent_branch_capacity_MVA_sum"]),
                "max_adjacent_branch_MVA": r4(record["max_adjacent_branch_MVA"]),
                "one_hop_neighbor_count": int(record["one_hop_neighbor_count"]),
                "one_hop_115kV_plus_neighbor_count": int(record["one_hop_115kV_plus_neighbor_count"]),
                "one_hop_generator_bus_count": int(record["one_hop_generator_bus_count"]),
                "one_hop_total_neighbor_load_MW": r4(record["one_hop_total_neighbor_load_MW"]),
            },
        }
    )

ranked.sort(
    key=lambda item: (
        -item["score"],
        -item["summary"]["adjacent_branch_capacity_MVA_sum"],
        item["bus"],
    )
)

for index, item in enumerate(ranked, start=1):
    item["rank"] = index

expected_report = {
    "screening_context": {
        "depot_name": config["depot_name"],
        "depot_peak_demand_MW": r4(config["depot_peak_demand_MW"]),
        "minimum_voltage_kV": r4(config["minimum_voltage_kV"]),
        "preferred_voltage_kV": r4(config["preferred_voltage_kV"]),
        "strong_branch_capacity_threshold_MVA": r4(config["strong_branch_capacity_threshold_MVA"]),
        "candidate_count": len(config["candidate_buses"]),
    },
    "status_summary": {
        "preferred_count": sum(1 for item in ranked if item["status"] == "preferred"),
        "conditional_count": sum(1 for item in ranked if item["status"] == "conditional"),
        "reject_count": sum(1 for item in ranked if item["status"] == "reject"),
        "recommended_bus_ids": [item["bus"] for item in ranked if item["status"] == "preferred"],
    },
    "ranked_candidates": ranked,
}

compare(report, expected_report)

statuses = {item["status"] for item in report["ranked_candidates"]}
if statuses != {"preferred", "conditional", "reject"}:
    raise AssertionError(f"expected three status classes, got {sorted(statuses)}")
