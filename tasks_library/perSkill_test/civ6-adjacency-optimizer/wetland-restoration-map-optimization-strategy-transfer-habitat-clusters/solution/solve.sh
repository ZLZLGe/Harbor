#!/bin/bash

python3 <<'PY'
import json
from itertools import combinations
from math import dist
from pathlib import Path

TASK_ROOT = Path.cwd().parent
SCENARIO_PATH = Path("/data/wetland_restoration_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/wetland_restoration_scenario.json"

OUTPUT_PATH = Path("/output/wetland_restoration_layout.json")
if not OUTPUT_PATH.parent.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/wetland_restoration_layout.json"


def site_catalog(scenario):
    return {
        "filter_island": scenario["candidate_sites"]["filter_islands"],
        "observation_point": scenario["candidate_sites"]["observation_points"],
        "trailhead": scenario["candidate_sites"]["trailheads"],
    }


def euclidean(a, b):
    return dist(tuple(a), tuple(b))


def site_is_legal(site, scenario):
    if site.get("blocked_by_waterway", False):
        return False
    for nest in scenario["sensitive_nests"]:
        if euclidean(site["coord"], nest["coord"]) <= nest["exclusion_radius"]:
            return False
    return True


def build_maps(scenario):
    legal_sites = {}
    coord_maps = {}
    for site_type, sites in site_catalog(scenario).items():
        filtered = [site for site in sites if site_is_legal(site, scenario)]
        legal_sites[site_type] = filtered
        coord_maps[site_type] = {site["id"]: tuple(site["coord"]) for site in filtered}
    return legal_sites, coord_maps


def same_type_ok(site_type, site_ids, scenario, coord_maps):
    minimum = scenario["interference_radii"]["same_type"][site_type]
    coords = [coord_maps[site_type][site_id] for site_id in site_ids]
    for left, right in combinations(coords, 2):
        if euclidean(left, right) < minimum:
            return False
    return True


def cross_type_ok(placements, scenario, coord_maps):
    rules = scenario["interference_radii"]["cross_type"]
    pairs = [
        ("filter_island", "observation_point"),
        ("filter_island", "trailhead"),
        ("observation_point", "trailhead"),
    ]
    for left_type, right_type in pairs:
        minimum = rules[f"{left_type}|{right_type}"]
        for left_id in placements[left_type]:
            for right_id in placements[right_type]:
                left_coord = coord_maps[left_type][left_id]
                right_coord = coord_maps[right_type][right_id]
                if euclidean(left_coord, right_coord) < minimum:
                    return False
    return True


def compute_cluster_scores(placements, scenario, coord_maps):
    coverage = scenario["coverage_radii"]
    cluster_scores = {}
    total_coverage = 0

    for cluster in scenario["habitat_clusters"]:
        covered_filters = [
            site_id
            for site_id in sorted(placements["filter_island"])
            if euclidean(coord_maps["filter_island"][site_id], cluster["coord"]) <= coverage["filter_island"]
        ]
        covered_observations = [
            site_id
            for site_id in sorted(placements["observation_point"])
            if euclidean(coord_maps["observation_point"][site_id], cluster["coord"]) <= coverage["observation_point"]
        ]
        covered_trailheads = [
            site_id
            for site_id in sorted(placements["trailhead"])
            if euclidean(coord_maps["trailhead"][site_id], cluster["coord"]) <= coverage["trailhead"]
        ]

        component_scores = {
            "filter_island": cluster["coverage_scores"]["filter_island"] if covered_filters else 0,
            "observation_point": cluster["coverage_scores"]["observation_point"] if covered_observations else 0,
            "trailhead": cluster["coverage_scores"]["trailhead"] if covered_trailheads else 0,
            "restoration_bonus": cluster["restoration_bonus"] if covered_filters and covered_observations else 0,
        }
        coverage_score = sum(component_scores.values())
        total_coverage += coverage_score

        cluster_scores[cluster["id"]] = {
            "covered_by": {
                "filter_islands": covered_filters,
                "observation_points": covered_observations,
                "trailheads": covered_trailheads,
            },
            "component_scores": component_scores,
            "coverage_score": coverage_score,
        }

    return cluster_scores, total_coverage


def compute_synergy(placements, scenario, coord_maps):
    filter_observation_links = []
    observation_trailhead_links = []

    fo_rule = scenario["synergy_rules"]["filter_observation"]
    for filter_id in sorted(placements["filter_island"]):
        for observation_id in sorted(placements["observation_point"]):
            if (
                euclidean(coord_maps["filter_island"][filter_id], coord_maps["observation_point"][observation_id])
                <= fo_rule["radius"]
            ):
                filter_observation_links.append(
                    {
                        "filter_island": filter_id,
                        "observation_point": observation_id,
                        "score": fo_rule["score"],
                    }
                )

    ot_rule = scenario["synergy_rules"]["observation_trailhead"]
    for observation_id in sorted(placements["observation_point"]):
        for trailhead_id in sorted(placements["trailhead"]):
            if (
                euclidean(coord_maps["observation_point"][observation_id], coord_maps["trailhead"][trailhead_id])
                <= ot_rule["radius"]
            ):
                observation_trailhead_links.append(
                    {
                        "observation_point": observation_id,
                        "trailhead": trailhead_id,
                        "score": ot_rule["score"],
                    }
                )

    total_synergy_score = sum(link["score"] for link in filter_observation_links)
    total_synergy_score += sum(link["score"] for link in observation_trailhead_links)

    return {
        "filter_observation_links": filter_observation_links,
        "observation_trailhead_links": observation_trailhead_links,
        "total_synergy_score": total_synergy_score,
    }


def evaluate(placements, scenario, coord_maps):
    cluster_scores, coverage_total = compute_cluster_scores(placements, scenario, coord_maps)
    synergy = compute_synergy(placements, scenario, coord_maps)
    total_score = coverage_total + synergy["total_synergy_score"]
    return {
        "placements": {
            "filter_islands": sorted(placements["filter_island"]),
            "observation_points": sorted(placements["observation_point"]),
            "trailheads": sorted(placements["trailhead"]),
        },
        "cluster_scores": cluster_scores,
        "facility_synergy": synergy,
        "total_score": total_score,
    }


with SCENARIO_PATH.open() as f:
    scenario = json.load(f)

legal_sites, coord_maps = build_maps(scenario)

best_solution = None
best_total = -1

for filter_choice in combinations(
    [site["id"] for site in legal_sites["filter_island"]],
    scenario["required_counts"]["filter_island"],
):
    if not same_type_ok("filter_island", filter_choice, scenario, coord_maps):
        continue
    for observation_choice in combinations(
        [site["id"] for site in legal_sites["observation_point"]],
        scenario["required_counts"]["observation_point"],
    ):
        if not same_type_ok("observation_point", observation_choice, scenario, coord_maps):
            continue
        for trailhead_choice in combinations(
            [site["id"] for site in legal_sites["trailhead"]],
            scenario["required_counts"]["trailhead"],
        ):
            if not same_type_ok("trailhead", trailhead_choice, scenario, coord_maps):
                continue
            placements = {
                "filter_island": filter_choice,
                "observation_point": observation_choice,
                "trailhead": trailhead_choice,
            }
            if not cross_type_ok(placements, scenario, coord_maps):
                continue
            candidate = evaluate(placements, scenario, coord_maps)
            if candidate["total_score"] > best_total:
                best_total = candidate["total_score"]
                best_solution = candidate

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w") as f:
    json.dump(best_solution, f, indent=2)

print(f"wetland_restoration_layout written to {OUTPUT_PATH}")
print(f"total_score: {best_solution['total_score']}")
PY
