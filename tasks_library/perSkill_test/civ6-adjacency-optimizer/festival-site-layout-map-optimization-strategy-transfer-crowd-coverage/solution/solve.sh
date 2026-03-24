#!/bin/bash

python3 <<'PY'
import json
from itertools import combinations
from math import dist
from pathlib import Path


TASK_ROOT = Path.cwd()
SCENARIO_PATH = Path("/data/festival_site_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/festival_site_scenario.json"

OUTPUT_PATH = Path("/output/festival_site_plan.json")
if not OUTPUT_PATH.parent.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/festival_site_plan.json"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def euclidean(a, b):
    return dist(tuple(a), tuple(b))


with SCENARIO_PATH.open() as f:
    scenario = json.load(f)

catalog = {
    facility_type: {site["id"]: tuple(site["coord"]) for site in sites}
    for facility_type, sites in scenario["candidate_sites"].items()
}


def stage_is_legal(site_id):
    coord = catalog["stages"][site_id]
    return all(
        euclidean(coord, quiet_zone["coord"]) > quiet_zone["buffer_radius"]
        for quiet_zone in scenario["quiet_zones"]
    )


def legal_ids(facility_type):
    restricted = set(scenario["restricted_sites"].get(facility_type, []))
    all_ids = [site["id"] for site in scenario["candidate_sites"][facility_type]]
    if facility_type == "stages":
        return [site_id for site_id in all_ids if site_id not in restricted and stage_is_legal(site_id)]
    return [site_id for site_id in all_ids if site_id not in restricted]


PAIR_TYPES = [
    ("stages", "supply_stations"),
    ("stages", "first_aid_points"),
    ("stages", "power_nodes"),
    ("supply_stations", "first_aid_points"),
    ("supply_stations", "power_nodes"),
    ("first_aid_points", "power_nodes"),
]


def same_type_ok(facility_type, selected_ids):
    minimum = scenario["spacing_rules"]["same_type"][facility_type]
    coords = [catalog[facility_type][site_id] for site_id in selected_ids]
    return all(euclidean(left, right) >= minimum for left, right in combinations(coords, 2))


def cross_type_ok(selection):
    for left_type, right_type in PAIR_TYPES:
        minimum = scenario["spacing_rules"]["cross_type"][f"{left_type}|{right_type}"]
        for left_id in selection[left_type]:
            for right_id in selection[right_type]:
                if euclidean(catalog[left_type][left_id], catalog[right_type][right_id]) < minimum:
                    return False
    return True


def compute_zone_coverage(selection):
    coverage = {}
    total_coverage = 0
    for zone in scenario["crowd_zones"]:
        stage_ids = sorted(
            site_id
            for site_id in selection["stages"]
            if euclidean(zone["coord"], catalog["stages"][site_id]) <= scenario["service_radii"]["stages"]
        )
        supply_ids = sorted(
            site_id
            for site_id in selection["supply_stations"]
            if euclidean(zone["coord"], catalog["supply_stations"][site_id])
            <= scenario["service_radii"]["supply_stations"]
        )
        aid_ids = sorted(
            site_id
            for site_id in selection["first_aid_points"]
            if euclidean(zone["coord"], catalog["first_aid_points"][site_id])
            <= scenario["service_radii"]["first_aid_points"]
        )
        component_scores = {
            "stage": round(
                zone["attendance"] * scenario["coverage_scores"]["stage_attendance_multiplier"]
            )
            if stage_ids
            else 0,
            "supply": zone["hydration_need"] * scenario["coverage_scores"]["supply_hydration_multiplier"]
            if supply_ids
            else 0,
            "first_aid": zone["medical_risk"] * scenario["coverage_scores"]["first_aid_risk_multiplier"]
            if aid_ids
            else 0,
            "dual_service_bonus": scenario["coverage_scores"]["dual_service_bonus"]
            if supply_ids and aid_ids
            else 0,
        }
        zone_total = sum(component_scores.values())
        total_coverage += zone_total
        coverage[zone["id"]] = {
            "covered_by": {
                "stages": stage_ids,
                "supply_stations": supply_ids,
                "first_aid_points": aid_ids,
            },
            "component_scores": component_scores,
            "zone_total": zone_total,
        }
    return coverage, total_coverage


def nearest_power_node(facility_type, site_id, selected_power_nodes):
    radius = scenario["power_rules"]["stage_radius"] if facility_type == "stages" else scenario["power_rules"]["supply_radius"]
    facility_coord = catalog[facility_type][site_id]
    candidates = []
    for power_id in selected_power_nodes:
        power_coord = catalog["power_nodes"][power_id]
        distance = euclidean(facility_coord, power_coord)
        if distance <= radius:
            candidates.append((distance, power_id))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][1]


def compute_power_links(selection):
    stage_links = []
    supply_links = []
    for stage_id in sorted(selection["stages"]):
        power_id = nearest_power_node("stages", stage_id, selection["power_nodes"])
        if power_id is not None:
            stage_links.append(
                {
                    "stage": stage_id,
                    "power_node": power_id,
                    "score": scenario["power_rules"]["stage_bonus_per_powered_stage"],
                }
            )
    for supply_id in sorted(selection["supply_stations"]):
        power_id = nearest_power_node("supply_stations", supply_id, selection["power_nodes"])
        if power_id is not None:
            supply_links.append(
                {
                    "supply_station": supply_id,
                    "power_node": power_id,
                    "score": scenario["power_rules"]["supply_bonus_per_powered_supply"],
                }
            )
    total_power_bonus = sum(link["score"] for link in stage_links) + sum(
        link["score"] for link in supply_links
    )
    return {
        "stage_links": stage_links,
        "supply_links": supply_links,
        "total_power_bonus": total_power_bonus,
    }


def build_output(selection):
    zone_coverage, coverage_score = compute_zone_coverage(selection)
    power_links = compute_power_links(selection)
    total_score = coverage_score + power_links["total_power_bonus"]
    return {
        "placements": {
            facility_type: [
                {"site_id": site_id, "coord": list(catalog[facility_type][site_id])}
                for site_id in selection[facility_type]
            ]
            for facility_type in ("stages", "supply_stations", "first_aid_points", "power_nodes")
        },
        "zone_coverage": zone_coverage,
        "power_links": power_links,
        "score_summary": {
            "coverage_score": coverage_score,
            "power_bonus": power_links["total_power_bonus"],
            "total_score": total_score,
        },
    }


best_output = None
best_score = -1

stage_ids = legal_ids("stages")
supply_ids = legal_ids("supply_stations")
aid_ids = legal_ids("first_aid_points")
power_ids = legal_ids("power_nodes")

for stages in combinations(stage_ids, scenario["required_counts"]["stages"]):
    if not same_type_ok("stages", stages):
        continue
    for supplies in combinations(supply_ids, scenario["required_counts"]["supply_stations"]):
        if not same_type_ok("supply_stations", supplies):
            continue
        for aid_points in combinations(aid_ids, scenario["required_counts"]["first_aid_points"]):
            if not same_type_ok("first_aid_points", aid_points):
                continue
            for powers in combinations(power_ids, scenario["required_counts"]["power_nodes"]):
                if not same_type_ok("power_nodes", powers):
                    continue
                selection = {
                    "stages": stages,
                    "supply_stations": supplies,
                    "first_aid_points": aid_points,
                    "power_nodes": powers,
                }
                if not cross_type_ok(selection):
                    continue
                output = build_output(selection)
                total_score = output["score_summary"]["total_score"]
                if total_score > best_score:
                    best_score = total_score
                    best_output = output

with OUTPUT_PATH.open("w") as f:
    json.dump(best_output, f, indent=2)

print(f"festival_site_plan written to {OUTPUT_PATH}")
print(f"total_score: {best_output['score_summary']['total_score']}")
PY
