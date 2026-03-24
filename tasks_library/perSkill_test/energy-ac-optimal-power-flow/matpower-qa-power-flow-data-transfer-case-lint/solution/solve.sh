#!/bin/bash
set -e

python3 <<'PY'
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


ISSUE_KEYS = [
    "duplicate_bus_ids",
    "missing_reference_bus",
    "generator_buses_missing",
    "branch_endpoints_missing",
    "isolated_online_subnetworks",
    "nonpositive_branch_ratings",
    "nonpositive_generator_pmax",
    "invalid_generator_q_ranges",
]


def resolve_cases_dir() -> Path:
    local_dir = Path.cwd() / "environment" / "cases"
    if local_dir.exists():
        return local_dir
    root_dir = Path("/root/cases")
    try:
        if root_dir.exists():
            return root_dir
    except PermissionError:
        pass
    return local_dir


def resolve_output_path() -> Path:
    root_output = Path("/root/case_lint_report.json")
    try:
        if root_output.parent.exists() and os.access(root_output.parent, os.W_OK):
            return root_output
    except PermissionError:
        pass
    return Path.cwd() / "case_lint_report.json"


def connected_components(nodes, adjacency):
    remaining = set(nodes)
    components = []
    while remaining:
        start = min(remaining)
        stack = [start]
        remaining.remove(start)
        buses = []
        while stack:
            current = stack.pop()
            buses.append(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        buses.sort()
        components.append(buses)
    return components


def analyze_case(case_path: Path) -> dict:
    data = json.loads(case_path.read_text(encoding="utf-8"))
    bus_rows = data["bus"]
    gen_rows = data["gen"]
    branch_rows = data["branch"]

    bus_ids = [int(row[0]) for row in bus_rows]
    bus_id_counts = Counter(bus_ids)
    bus_id_set = set(bus_ids)

    duplicate_bus_ids = sorted(bus_id for bus_id, count in bus_id_counts.items() if count > 1)
    reference_bus_ids = sorted(int(row[0]) for row in bus_rows if int(row[1]) == 3)
    missing_reference_bus = len(reference_bus_ids) == 0

    generator_buses_missing = []
    online_generator_ids_by_bus = defaultdict(list)
    for generator_id, row in enumerate(gen_rows, start=1):
        bus_id = int(row[0])
        if bus_id not in bus_id_set:
            generator_buses_missing.append({"generator_id": generator_id, "bus": bus_id})
            continue
        if int(row[7]) == 1:
            online_generator_ids_by_bus[bus_id].append(generator_id)
    generator_buses_missing.sort(key=lambda item: (item["generator_id"], item["bus"]))

    branch_endpoints_missing = []
    active_valid_branch_records = []
    adjacency = defaultdict(set)
    for branch_id, row in enumerate(branch_rows, start=1):
        from_bus = int(row[0])
        to_bus = int(row[1])
        has_missing_endpoint = from_bus not in bus_id_set or to_bus not in bus_id_set
        if has_missing_endpoint:
            branch_endpoints_missing.append(
                {"branch_id": branch_id, "from_bus": from_bus, "to_bus": to_bus}
            )
            continue
        if int(row[10]) == 1:
            active_valid_branch_records.append((branch_id, from_bus, to_bus))
            adjacency[from_bus].add(to_bus)
            adjacency[to_bus].add(from_bus)
    branch_endpoints_missing.sort(key=lambda item: item["branch_id"])

    participating_buses = set()
    for _, from_bus, to_bus in active_valid_branch_records:
        participating_buses.add(from_bus)
        participating_buses.add(to_bus)
    participating_buses.update(online_generator_ids_by_bus.keys())

    isolated_online_subnetworks = []
    if len(participating_buses) > 0:
        for bus_id in participating_buses:
            adjacency.setdefault(bus_id, set())
        components = []
        for buses in connected_components(participating_buses, adjacency):
            branch_ids = sorted(
                branch_id
                for branch_id, from_bus, to_bus in active_valid_branch_records
                if from_bus in buses and to_bus in buses
            )
            generator_ids = sorted(
                generator_id
                for bus_id in buses
                for generator_id in online_generator_ids_by_bus.get(bus_id, [])
            )
            components.append(
                {
                    "bus_ids": buses,
                    "bus_count": len(buses),
                    "online_generator_ids": generator_ids,
                    "online_generator_count": len(generator_ids),
                    "online_branch_ids": branch_ids,
                    "online_branch_count": len(branch_ids),
                }
            )

        components.sort(
            key=lambda item: (
                -item["bus_count"],
                -item["online_generator_count"],
                min(item["bus_ids"]),
            )
        )

        for index, component in enumerate(components[1:], start=1):
            isolated_online_subnetworks.append(
                {
                    "subnetwork_id": f"island_{index}",
                    "bus_ids": component["bus_ids"],
                    "bus_count": component["bus_count"],
                    "online_generator_ids": component["online_generator_ids"],
                    "online_generator_count": component["online_generator_count"],
                    "online_branch_ids": component["online_branch_ids"],
                    "online_branch_count": component["online_branch_count"],
                }
            )

    nonpositive_branch_ratings = []
    for branch_id, row in enumerate(branch_rows, start=1):
        rate_a = float(row[5])
        if rate_a <= 0:
            nonpositive_branch_ratings.append(
                {
                    "branch_id": branch_id,
                    "from_bus": int(row[0]),
                    "to_bus": int(row[1]),
                    "rateA": rate_a,
                }
            )

    nonpositive_generator_pmax = []
    invalid_generator_q_ranges = []
    for generator_id, row in enumerate(gen_rows, start=1):
        pmax = float(row[8])
        qmax = float(row[3])
        qmin = float(row[4])
        if pmax <= 0:
            nonpositive_generator_pmax.append(
                {
                    "generator_id": generator_id,
                    "bus": int(row[0]),
                    "pmax_MW": pmax,
                }
            )
        if qmax <= qmin:
            invalid_generator_q_ranges.append(
                {
                    "generator_id": generator_id,
                    "bus": int(row[0]),
                    "qmin_MVAr": qmin,
                    "qmax_MVAr": qmax,
                }
            )

    issue_counts = {
        "duplicate_bus_ids": len(duplicate_bus_ids),
        "missing_reference_bus": 1 if missing_reference_bus else 0,
        "generator_buses_missing": len(generator_buses_missing),
        "branch_endpoints_missing": len(branch_endpoints_missing),
        "isolated_online_subnetworks": len(isolated_online_subnetworks),
        "nonpositive_branch_ratings": len(nonpositive_branch_ratings),
        "nonpositive_generator_pmax": len(nonpositive_generator_pmax),
        "invalid_generator_q_ranges": len(invalid_generator_q_ranges),
    }
    issue_counts["total"] = sum(issue_counts[key] for key in ISSUE_KEYS)

    return {
        "case_id": case_path.stem,
        "source_file": f"cases/{case_path.name}",
        "bus_count": len(bus_rows),
        "generator_count": len(gen_rows),
        "branch_count": len(branch_rows),
        "reference_bus_ids": reference_bus_ids,
        "issue_counts": issue_counts,
        "issues": {
            "duplicate_bus_ids": duplicate_bus_ids,
            "missing_reference_bus": missing_reference_bus,
            "generator_buses_missing": generator_buses_missing,
            "branch_endpoints_missing": branch_endpoints_missing,
            "isolated_online_subnetworks": isolated_online_subnetworks,
            "nonpositive_branch_ratings": nonpositive_branch_ratings,
            "nonpositive_generator_pmax": nonpositive_generator_pmax,
            "invalid_generator_q_ranges": invalid_generator_q_ranges,
        },
    }


def main():
    cases_dir = resolve_cases_dir()
    case_paths = sorted(cases_dir.glob("*.json"))
    cases = [analyze_case(case_path) for case_path in case_paths]

    issue_type_counts = {
        key: sum(case["issue_counts"][key] for case in cases)
        for key in ISSUE_KEYS
    }
    report = {
        "portfolio_summary": {
            "case_count": len(cases),
            "cases_with_any_issue": sum(1 for case in cases if case["issue_counts"]["total"] > 0),
            "total_issue_count": sum(issue_type_counts.values()),
            "issue_type_counts": issue_type_counts,
        },
        "cases": cases,
    }

    output_path = resolve_output_path()
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
