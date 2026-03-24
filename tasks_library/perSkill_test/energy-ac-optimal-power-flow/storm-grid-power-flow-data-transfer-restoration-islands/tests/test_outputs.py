import json
import os
from collections import defaultdict, deque
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
    root_path = Path("/root/restoration_islands_report.json")
    try:
        root_exists = root_path.exists()
    except PermissionError:
        root_exists = False
    if root_exists:
        return root_path
    return TASK_DIR / "restoration_islands_report.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def positive(value: float) -> float:
    return value if value > 0 else 0.0


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
outages = load_json(resolve_path("OUTAGES_FILE", "storm_outages.json", "storm_outages.json"))
critical = load_json(resolve_path("CRITICAL_LOADS_FILE", "critical_loads.json", "critical_loads.json"))
report = load_json(resolve_output())

required_top_keys = {
    "summary",
    "critical_load_coverage",
    "energized_islands",
    "de_energized_components",
}
if set(report.keys()) != required_top_keys:
    raise AssertionError(f"unexpected top-level keys: {sorted(report.keys())}")

bus_ids = [int(row[0]) for row in network["bus"]]

critical_bus_ids = sorted({int(item["bus"]) for item in critical["critical_loads"]})
critical_bus_set = set(critical_bus_ids)
bus_load_mw = {int(row[0]): positive(float(row[2])) for row in network["bus"]}
bus_load_mvar = {int(row[0]): positive(float(row[3])) for row in network["bus"]}

outaged_branch_keys = {
    tuple(sorted((int(item["from_bus"]), int(item["to_bus"]))))
    for item in outages["branch_outages"]
}
outaged_generator_ids = {int(item["id"]) for item in outages["generator_outages"]}

adjacency = defaultdict(set)
active_branch_count = 0
for row in network["branch"]:
    if int(row[10]) != 1:
        continue
    from_bus = int(row[0])
    to_bus = int(row[1])
    if tuple(sorted((from_bus, to_bus))) in outaged_branch_keys:
        continue
    adjacency[from_bus].add(to_bus)
    adjacency[to_bus].add(from_bus)
    active_branch_count += 1

for bus_id in bus_ids:
    adjacency.setdefault(bus_id, set())

available_generation_mw_by_bus = defaultdict(float)
online_generator_count_by_bus = defaultdict(int)
available_generator_count = 0
for generator_id, row in enumerate(network["gen"], start=1):
    if int(row[7]) != 1 or generator_id in outaged_generator_ids:
        continue
    pmax = positive(float(row[8]))
    if pmax <= 0:
        continue
    bus_id = int(row[0])
    available_generation_mw_by_bus[bus_id] += pmax
    online_generator_count_by_bus[bus_id] += 1
    available_generator_count += 1

components = []
visited = set()
for bus_id in sorted(bus_ids):
    if bus_id in visited:
        continue
    queue = deque([bus_id])
    visited.add(bus_id)
    component_bus_ids = []
    while queue:
        current = queue.popleft()
        component_bus_ids.append(current)
        for neighbor in sorted(adjacency[current]):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append(neighbor)

    component_bus_ids.sort()
    load_mw = sum(bus_load_mw[component_bus] for component_bus in component_bus_ids)
    load_mvar = sum(bus_load_mvar[component_bus] for component_bus in component_bus_ids)
    available_generation_mw = sum(
        available_generation_mw_by_bus[component_bus] for component_bus in component_bus_ids
    )
    critical_bus_ids_in_component = [
        component_bus for component_bus in component_bus_ids if component_bus in critical_bus_set
    ]
    components.append(
        {
            "min_bus_id": component_bus_ids[0],
            "representative_bus_ids": component_bus_ids[:10],
            "bus_count": len(component_bus_ids),
            "load_MW": round(load_mw, 4),
            "load_MVAr": round(load_mvar, 4),
            "available_generation_MW": round(available_generation_mw, 4),
            "generation_margin_MW": round(available_generation_mw - load_mw, 4),
            "online_generator_count": sum(
                online_generator_count_by_bus[component_bus] for component_bus in component_bus_ids
            ),
            "generator_bus_ids": [
                component_bus
                for component_bus in component_bus_ids
                if available_generation_mw_by_bus[component_bus] > 0
            ],
            "critical_load_bus_ids": critical_bus_ids_in_component,
            "critical_load_MW": round(
                sum(bus_load_mw[component_bus] for component_bus in critical_bus_ids_in_component), 4
            ),
        }
    )

energized = [component for component in components if component["available_generation_MW"] > 0]
dark = [component for component in components if component["available_generation_MW"] <= 0]

energized.sort(key=lambda item: (-item["load_MW"], -item["available_generation_MW"], item["min_bus_id"]))
dark.sort(key=lambda item: (-item["load_MW"], item["min_bus_id"]))

expected_report = {
    "summary": {
        "total_bus_count": len(bus_ids),
        "active_branch_count": active_branch_count,
        "available_generator_count": available_generator_count,
        "energized_island_count": len(energized),
        "de_energized_component_count": len(dark),
        "topology_disconnected_load_MW": round(sum(component["load_MW"] for component in dark), 4),
        "topology_disconnected_load_MVAr": round(sum(component["load_MVAr"] for component in dark), 4),
    },
    "critical_load_coverage": {
        "total_count": len(critical_bus_ids),
        "served_count": sum(len(component["critical_load_bus_ids"]) for component in energized),
        "unserved_count": sum(len(component["critical_load_bus_ids"]) for component in dark),
        "served_MW": round(sum(component["critical_load_MW"] for component in energized), 4),
        "unserved_MW": round(sum(component["critical_load_MW"] for component in dark), 4),
        "served_bus_ids": sorted(
            bus_id for component in energized for bus_id in component["critical_load_bus_ids"]
        ),
        "unserved_bus_ids": sorted(
            bus_id for component in dark for bus_id in component["critical_load_bus_ids"]
        ),
    },
    "energized_islands": [
        {
            "island_id": f"island_{index}",
            "representative_bus_ids": component["representative_bus_ids"],
            "bus_count": component["bus_count"],
            "load_MW": component["load_MW"],
            "load_MVAr": component["load_MVAr"],
            "available_generation_MW": component["available_generation_MW"],
            "generation_margin_MW": component["generation_margin_MW"],
            "online_generator_count": component["online_generator_count"],
            "generator_bus_ids": component["generator_bus_ids"],
            "critical_load_bus_ids": component["critical_load_bus_ids"],
            "critical_load_MW": component["critical_load_MW"],
        }
        for index, component in enumerate(energized, start=1)
    ],
    "de_energized_components": [
        {
            "component_id": f"component_{index}",
            "representative_bus_ids": component["representative_bus_ids"],
            "bus_count": component["bus_count"],
            "load_MW": component["load_MW"],
            "load_MVAr": component["load_MVAr"],
            "critical_load_bus_ids": component["critical_load_bus_ids"],
            "critical_load_MW": component["critical_load_MW"],
        }
        for index, component in enumerate(dark, start=1)
    ],
}

compare(report, expected_report)

if report["summary"]["energized_island_count"] < 2:
    raise AssertionError("expected multiple energized islands in this transfer task")
if report["summary"]["de_energized_component_count"] < 1:
    raise AssertionError("expected at least one de-energized component in this transfer task")
