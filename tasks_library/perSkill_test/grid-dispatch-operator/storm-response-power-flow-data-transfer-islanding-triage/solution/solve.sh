#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f /root/storm_network.json ] && [ -f /root/storm_outages.json ]; then
  NETWORK_FILE="/root/storm_network.json"
  OUTAGE_FILE="/root/storm_outages.json"
  OUTPUT_FILE="/root/islanding_triage.json"
else
  NETWORK_FILE="$TASK_DIR/environment/storm_network.json"
  OUTAGE_FILE="$TASK_DIR/environment/storm_outages.json"
  OUTPUT_FILE="$TASK_DIR/islanding_triage.json"
fi

python3 - "$NETWORK_FILE" "$OUTAGE_FILE" "$OUTPUT_FILE" <<'PY'
import json
import sys
from collections import deque
from pathlib import Path


def round2(value):
    rounded = round(float(value), 2)
    return 0.0 if rounded == -0.0 else rounded


def normalize_pair(a, b):
    first = int(a)
    second = int(b)
    return (first, second) if first < second else (second, first)


network_path = Path(sys.argv[1])
outage_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

with network_path.open(encoding="utf-8") as f:
    network = json.load(f)

with outage_path.open(encoding="utf-8") as f:
    outage_data = json.load(f)

buses = network["bus"]
gens = network["gen"]
branches = network["branch"]

bus_numbers = sorted(int(row[0]) for row in buses)
bus_loads = {int(row[0]): float(row[2]) for row in buses}

online_generation = {bus: 0.0 for bus in bus_numbers}
for row in gens:
    if int(row[7]) != 1:
        continue
    online_generation[int(row[0])] = online_generation.get(int(row[0]), 0.0) + float(row[8])

outage_pairs = sorted(
    {normalize_pair(line["from"], line["to"]) for line in outage_data["outaged_lines"]}
)
outage_set = set(outage_pairs)

adjacency = {bus: set() for bus in bus_numbers}
for row in branches:
    if int(row[10]) != 1:
        continue
    pair = normalize_pair(row[0], row[1])
    if pair in outage_set:
        continue
    a, b = pair
    adjacency[a].add(b)
    adjacency[b].add(a)

components = []
seen = set()
for bus in bus_numbers:
    if bus in seen:
        continue
    queue = deque([bus])
    seen.add(bus)
    component = []
    while queue:
        current = queue.popleft()
        component.append(current)
        for neighbor in sorted(adjacency[current]):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)
    components.append(sorted(component))

components.sort(key=lambda buses_in_island: buses_in_island[0])

islands = []
for island_id, component in enumerate(components, start=1):
    component_set = set(component)
    stranded_load = sum(bus_loads[bus] for bus in component)
    surviving_generation = sum(online_generation.get(bus, 0.0) for bus in component)
    responsible_outages = [
        {"from": pair[0], "to": pair[1]}
        for pair in outage_pairs
        if (pair[0] in component_set) ^ (pair[1] in component_set)
    ]
    islands.append(
        {
            "island_id": island_id,
            "isolated_buses": component,
            "stranded_load_MW": round2(stranded_load),
            "surviving_generation_MW": round2(surviving_generation),
            "generation_minus_load_MW": round2(surviving_generation - stranded_load),
            "responsible_outage_lines": responsible_outages,
        }
    )

report = {
    "island_count": len(islands),
    "totals": {
        "stranded_load_MW": round2(sum(bus_loads.values())),
        "surviving_generation_MW": round2(sum(online_generation.values())),
    },
    "islands": islands,
}

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
    f.write("\n")
PY
