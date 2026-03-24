#!/usr/bin/env python3

import json
from itertools import combinations
from math import dist
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = Path("/data/festival_site_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/festival_site_scenario.json"

OUTPUT_PATH = Path("/output/festival_site_plan.json")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/festival_site_plan.json"

SCORE_PATH = Path("/logs/verifier/scores/festival_site_plan.txt")
if not SCORE_PATH.parent.exists():
    SCORE_PATH = TASK_ROOT / ".tmp_logs/verifier/scores/festival_site_plan.txt"


PAIR_TYPES = [
    ("stages", "supply_stations"),
    ("stages", "first_aid_points"),
    ("stages", "power_nodes"),
    ("supply_stations", "first_aid_points"),
    ("supply_stations", "power_nodes"),
    ("first_aid_points", "power_nodes"),
]


def fail(message):
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text("0.0")
    raise AssertionError(message)


def euclidean(a, b):
    return dist(tuple(a), tuple(b))


def load_json(path):
    with path.open() as f:
        return json.load(f)


def site_catalog(scenario):
    return {
        facility_type: {site["id"]: tuple(site["coord"]) for site in sites}
        for facility_type, sites in scenario["candidate_sites"].items()
    }


def legal_ids(scenario, catalog):
    result = {}
    quiet_zones = scenario["quiet_zones"]
    restricted = scenario["restricted_sites"]
    for facility_type, site_map in catalog.items():
        allowed = []
        for site_id, coord in site_map.items():
            if site_id in restricted.get(facility_type, []):
                continue
            if facility_type == "stages":
                if any(
                    euclidean(coord, quiet_zone["coord"]) <= quiet_zone["buffer_radius"]
                    for quiet_zone in quiet_zones
                ):
                    continue
            allowed.append(site_id)
        result[facility_type] = sorted(allowed)
    return result


def normalize_placements(placements, scenario, catalog):
    normalized = {}
    required_counts = scenario["required_counts"]
    expected_types = ("stages", "supply_stations", "first_aid_points", "power_nodes")

    if set(placements) != set(expected_types):
        fail("placements keys are incorrect")

    for facility_type in expected_types:
        entries = placements[facility_type]
        if not isinstance(entries, list):
            fail(f"{facility_type} placements must be a list")
        if len(entries) != required_counts[facility_type]:
            fail(f"{facility_type} placement count is incorrect")

        seen_ids = set()
        normalized_entries = []
        for entry in entries:
            if set(entry) != {"site_id", "coord"}:
                fail(f"{facility_type} placement entries must contain site_id and coord")
            site_id = entry["site_id"]
            coord = entry["coord"]
            if not isinstance(site_id, str):
                fail(f"{facility_type} site_id must be a string")
            if site_id in seen_ids:
                fail(f"duplicate {facility_type} site_id: {site_id}")
            if site_id not in catalog[facility_type]:
                fail(f"unknown {facility_type} site_id: {site_id}")
            if not isinstance(coord, list) or len(coord) != 2 or not all(isinstance(v, int) for v in coord):
                fail(f"{facility_type} coord must be a two-integer list")
            if tuple(coord) != catalog[facility_type][site_id]:
                fail(f"{facility_type} coord does not match scenario for {site_id}")
            seen_ids.add(site_id)
            normalized_entries.append(site_id)
        normalized[facility_type] = tuple(normalized_entries)
    return normalized


def same_type_ok(facility_type, selected_ids, scenario, catalog):
    minimum = scenario["spacing_rules"]["same_type"][facility_type]
    coords = [catalog[facility_type][site_id] for site_id in selected_ids]
    return all(euclidean(left, right) >= minimum for left, right in combinations(coords, 2))


def cross_type_ok(selection, scenario, catalog):
    for left_type, right_type in PAIR_TYPES:
        minimum = scenario["spacing_rules"]["cross_type"][f"{left_type}|{right_type}"]
        for left_id in selection[left_type]:
            for right_id in selection[right_type]:
                if euclidean(catalog[left_type][left_id], catalog[right_type][right_id]) < minimum:
                    return False
    return True


def compute_zone_coverage(selection, scenario, catalog):
    zone_coverage = {}
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
        zone_coverage[zone["id"]] = {
            "covered_by": {
                "stages": stage_ids,
                "supply_stations": supply_ids,
                "first_aid_points": aid_ids,
            },
            "component_scores": component_scores,
            "zone_total": zone_total,
        }
    return zone_coverage, total_coverage


def nearest_power_node(facility_type, site_id, selected_power_nodes, scenario, catalog):
    radius = (
        scenario["power_rules"]["stage_radius"]
        if facility_type == "stages"
        else scenario["power_rules"]["supply_radius"]
    )
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


def compute_power_links(selection, scenario, catalog):
    stage_links = []
    supply_links = []

    for stage_id in sorted(selection["stages"]):
        power_id = nearest_power_node("stages", stage_id, selection["power_nodes"], scenario, catalog)
        if power_id is not None:
            stage_links.append(
                {
                    "stage": stage_id,
                    "power_node": power_id,
                    "score": scenario["power_rules"]["stage_bonus_per_powered_stage"],
                }
            )

    for supply_id in sorted(selection["supply_stations"]):
        power_id = nearest_power_node(
            "supply_stations", supply_id, selection["power_nodes"], scenario, catalog
        )
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


def evaluate(selection, scenario, catalog):
    zone_coverage, coverage_score = compute_zone_coverage(selection, scenario, catalog)
    power_links = compute_power_links(selection, scenario, catalog)
    total_score = coverage_score + power_links["total_power_bonus"]
    return zone_coverage, power_links, coverage_score, total_score


def optimal_total(scenario, legal, catalog):
    best_total = -1
    for stages in combinations(legal["stages"], scenario["required_counts"]["stages"]):
        if not same_type_ok("stages", stages, scenario, catalog):
            continue
        for supplies in combinations(legal["supply_stations"], scenario["required_counts"]["supply_stations"]):
            if not same_type_ok("supply_stations", supplies, scenario, catalog):
                continue
            for aid_points in combinations(
                legal["first_aid_points"], scenario["required_counts"]["first_aid_points"]
            ):
                if not same_type_ok("first_aid_points", aid_points, scenario, catalog):
                    continue
                for powers in combinations(legal["power_nodes"], scenario["required_counts"]["power_nodes"]):
                    if not same_type_ok("power_nodes", powers, scenario, catalog):
                        continue
                    selection = {
                        "stages": stages,
                        "supply_stations": supplies,
                        "first_aid_points": aid_points,
                        "power_nodes": powers,
                    }
                    if not cross_type_ok(selection, scenario, catalog):
                        continue
                    _, _, _, total_score = evaluate(selection, scenario, catalog)
                    best_total = max(best_total, total_score)
    return best_total


def main():
    if not SCENARIO_PATH.exists():
        fail(f"scenario file not found: {SCENARIO_PATH}")
    if not OUTPUT_PATH.exists():
        fail(f"solution file not found: {OUTPUT_PATH}")

    scenario = load_json(SCENARIO_PATH)
    solution = load_json(OUTPUT_PATH)
    catalog = site_catalog(scenario)
    legal = legal_ids(scenario, catalog)

    if set(solution) != {"placements", "zone_coverage", "power_links", "score_summary"}:
        fail("top-level keys do not match the required schema")

    selection = normalize_placements(solution["placements"], scenario, catalog)

    for facility_type, chosen_ids in selection.items():
        for site_id in chosen_ids:
            if site_id not in legal[facility_type]:
                fail(f"illegal {facility_type} site selected: {site_id}")
        if not same_type_ok(facility_type, chosen_ids, scenario, catalog):
            fail(f"{facility_type} violates same-type spacing")

    if not cross_type_ok(selection, scenario, catalog):
        fail("cross-type spacing is violated")

    expected_zone_coverage, expected_power_links, coverage_score, total_score = evaluate(
        selection, scenario, catalog
    )

    expected_zone_ids = {zone["id"] for zone in scenario["crowd_zones"]}
    if set(solution["zone_coverage"]) != expected_zone_ids:
        fail("zone_coverage keys do not match crowd zones")
    if solution["zone_coverage"] != expected_zone_coverage:
        fail("zone_coverage does not match recomputed values")

    if solution["power_links"] != expected_power_links:
        fail("power_links do not match recomputed values")

    summary = solution["score_summary"]
    if set(summary) != {"coverage_score", "power_bonus", "total_score"}:
        fail("score_summary keys are incorrect")
    expected_summary = {
        "coverage_score": coverage_score,
        "power_bonus": expected_power_links["total_power_bonus"],
        "total_score": total_score,
    }
    if summary != expected_summary:
        fail("score_summary does not match recomputed totals")

    best_total = optimal_total(scenario, legal, catalog)
    score = total_score / best_total if best_total > 0 else 0.0
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(str(score))

    if total_score != best_total:
        fail(f"submitted total_score {total_score} != optimal {best_total}")

    print("festival_site_plan verification passed")


if __name__ == "__main__":
    main()
