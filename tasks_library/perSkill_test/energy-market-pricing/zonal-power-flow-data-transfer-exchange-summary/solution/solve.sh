#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from collections import defaultdict


def round2(value):
    return round(float(value), 2)


with open("/root/network.json", encoding="utf-8") as f:
    network = json.load(f)

with open("/root/zones.json", encoding="utf-8") as f:
    zone_data = json.load(f)

zone_order = [item["zone_id"] for item in zone_data["zone_definitions"]]
zone_name_by_id = {item["zone_id"]: item["zone_name"] for item in zone_data["zone_definitions"]}
bus_to_zone = {int(bus): zone_id for bus, zone_id in zone_data["bus_to_zone"].items()}

zone_buses = {zone_id: [] for zone_id in zone_order}
bus_rows = {}
for row in network["bus"]:
    bus_number = int(row[0])
    bus_rows[bus_number] = row
    zone_buses[bus_to_zone[bus_number]].append(bus_number)

zone_generation_capacity = defaultdict(float)
zone_reserve_capacity = defaultdict(float)
for index, gen in enumerate(network["gen"]):
    if int(gen[7]) != 1:
        continue
    zone_id = bus_to_zone[int(gen[0])]
    zone_generation_capacity[zone_id] += float(gen[8])
    zone_reserve_capacity[zone_id] += float(network["reserve_capacity"][index])

zones = []
for zone_id in zone_order:
    reference_bus_numbers = sorted(
        bus_number
        for bus_number in zone_buses[zone_id]
        if int(bus_rows[bus_number][1]) == 3
    )
    total_effective_load = sum(max(float(bus_rows[bus_number][2]), 0.0) for bus_number in zone_buses[zone_id])
    zones.append(
        {
            "zone_id": zone_id,
            "zone_name": zone_name_by_id[zone_id],
            "bus_count": len(zone_buses[zone_id]),
            "total_effective_load_mw": round2(total_effective_load),
            "total_generation_capacity_mw": round2(zone_generation_capacity[zone_id]),
            "total_reserve_capacity_mw": round2(zone_reserve_capacity[zone_id]),
            "reference_bus_numbers": reference_bus_numbers,
            "has_reference_bus": bool(reference_bus_numbers),
        }
    )

interface_totals = defaultdict(lambda: {"active_branch_count": 0, "total_rating_mw": 0.0})
for branch in network["branch"]:
    if int(branch[10]) != 1:
        continue
    zone_a = bus_to_zone[int(branch[0])]
    zone_b = bus_to_zone[int(branch[1])]
    if zone_a == zone_b:
        continue
    from_zone, to_zone = sorted((zone_a, zone_b))
    key = (from_zone, to_zone)
    interface_totals[key]["active_branch_count"] += 1
    interface_totals[key]["total_rating_mw"] += float(branch[5])

interzonal_interfaces = []
for from_zone, to_zone in sorted(interface_totals):
    totals = interface_totals[(from_zone, to_zone)]
    interzonal_interfaces.append(
        {
            "interface_id": f"{from_zone}__{to_zone}",
            "from_zone": from_zone,
            "to_zone": to_zone,
            "active_branch_count": totals["active_branch_count"],
            "total_rating_mw": round2(totals["total_rating_mw"]),
        }
    )

output = {
    "network_name": network["name"],
    "zone_dataset": zone_data["dataset_name"],
    "zone_count": len(zones),
    "interzonal_interface_count": len(interzonal_interfaces),
    "effective_load_rule": "effective_load_mw = max(Pd, 0)",
    "zones": zones,
    "interzonal_interfaces": interzonal_interfaces,
}

with open("/root/zone_exchange_summary.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
    f.write("\n")
PY
