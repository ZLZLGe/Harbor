#!/usr/bin/env python3

import json
from itertools import combinations
from math import dist
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = Path("/data/wetland_restoration_scenario.json")
if not SCENARIO_PATH.exists():
    SCENARIO_PATH = TASK_ROOT / "environment/data/wetland_restoration_scenario.json"

OUTPUT_PATH = Path("/output/wetland_restoration_layout.json")
if not OUTPUT_PATH.exists():
    OUTPUT_PATH = TASK_ROOT / ".tmp_output/wetland_restoration_layout.json"

SCORE_PATH = Path("/logs/verifier/scores/wetland_restoration_layout.txt")
if not SCORE_PATH.parent.exists():
    SCORE_PATH = TASK_ROOT / ".tmp_logs/verifier/scores/wetland_restoration_layout.txt"


def euclidean(a, b):
    return dist(tuple(a), tuple(b))


def site_catalog(scenario):
    return {
        "filter_island": scenario["candidate_sites"]["filter_islands"],
        "observation_point": scenario["candidate_sites"]["observation_points"],
        "trailhead": scenario["candidate_sites"]["trailheads"],
    }


def legal_site_ids(scenario):
    result = {}
    coord_maps = {}
    all_ids = {}
    for site_type, sites in site_catalog(scenario).items():
        legal = []
        coords = {}
        ids = {}
        for site in sites:
            ids[site["id"]] = tuple(site["coord"])
            blocked = site.get("blocked_by_waterway", False)
            inside_nest = any(
                euclidean(site["coord"], nest["coord"]) <= nest["exclusion_radius"]
                for nest in scenario["sensitive_nests"]
            )
            if blocked or inside_nest:
                continue
            legal.append(site["id"])
            coords[site["id"]] = tuple(site["coord"])
        result[site_type] = legal
        coord_maps[site_type] = coords
        all_ids[site_type] = ids
    return result, coord_maps, all_ids


def same_type_ok(site_type, site_ids, scenario, coord_maps):
    minimum = scenario["interference_radii"]["same_type"][site_type]
    coords = [coord_maps[site_type][site_id] for site_id in site_ids]
    return all(euclidean(left, right) >= minimum for left, right in combinations(coords, 2))


def cross_type_ok(placements, scenario, coord_maps):
    pairs = [
        ("filter_island", "observation_point"),
        ("filter_island", "trailhead"),
        ("observation_point", "trailhead"),
    ]
    rules = scenario["interference_radii"]["cross_type"]
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
        filters = [
            site_id
            for site_id in sorted(placements["filter_island"])
            if euclidean(coord_maps["filter_island"][site_id], cluster["coord"]) <= coverage["filter_island"]
        ]
        observations = [
            site_id
            for site_id in sorted(placements["observation_point"])
            if euclidean(coord_maps["observation_point"][site_id], cluster["coord"]) <= coverage["observation_point"]
        ]
        trailheads = [
            site_id
            for site_id in sorted(placements["trailhead"])
            if euclidean(coord_maps["trailhead"][site_id], cluster["coord"]) <= coverage["trailhead"]
        ]
        component_scores = {
            "filter_island": cluster["coverage_scores"]["filter_island"] if filters else 0,
            "observation_point": cluster["coverage_scores"]["observation_point"] if observations else 0,
            "trailhead": cluster["coverage_scores"]["trailhead"] if trailheads else 0,
            "restoration_bonus": cluster["restoration_bonus"] if filters and observations else 0,
        }
        coverage_score = sum(component_scores.values())
        total_coverage += coverage_score
        cluster_scores[cluster["id"]] = {
            "covered_by": {
                "filter_islands": filters,
                "observation_points": observations,
                "trailheads": trailheads,
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

    total_synergy = sum(link["score"] for link in filter_observation_links)
    total_synergy += sum(link["score"] for link in observation_trailhead_links)
    return {
        "filter_observation_links": filter_observation_links,
        "observation_trailhead_links": observation_trailhead_links,
        "total_synergy_score": total_synergy,
    }


def evaluate(placements, scenario, coord_maps):
    cluster_scores, coverage_total = compute_cluster_scores(placements, scenario, coord_maps)
    synergy = compute_synergy(placements, scenario, coord_maps)
    total_score = coverage_total + synergy["total_synergy_score"]
    return cluster_scores, synergy, total_score


def optimal_total(scenario, legal_ids, coord_maps):
    best_total = -1
    for filter_choice in combinations(
        legal_ids["filter_island"],
        scenario["required_counts"]["filter_island"],
    ):
        if not same_type_ok("filter_island", filter_choice, scenario, coord_maps):
            continue
        for observation_choice in combinations(
            legal_ids["observation_point"],
            scenario["required_counts"]["observation_point"],
        ):
            if not same_type_ok("observation_point", observation_choice, scenario, coord_maps):
                continue
            for trailhead_choice in combinations(
                legal_ids["trailhead"],
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
                _, _, total = evaluate(placements, scenario, coord_maps)
                best_total = max(best_total, total)
    return best_total


def fail(message):
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text("0.0")
    raise AssertionError(message)


def main():
    assert SCENARIO_PATH.exists(), f"scenario file not found: {SCENARIO_PATH}"
    assert OUTPUT_PATH.exists(), f"solution file not found: {OUTPUT_PATH}"

    with SCENARIO_PATH.open() as f:
        scenario = json.load(f)
    with OUTPUT_PATH.open() as f:
        solution = json.load(f)

    legal_ids, coord_maps, all_ids = legal_site_ids(scenario)

    if set(solution) != {"placements", "cluster_scores", "facility_synergy", "total_score"}:
        fail("top-level keys do not match the required schema")

    placements = solution["placements"]
    if set(placements) != {"filter_islands", "observation_points", "trailheads"}:
        fail("placements keys are incorrect")

    counts = scenario["required_counts"]
    filter_ids = placements["filter_islands"]
    observation_ids = placements["observation_points"]
    trailhead_ids = placements["trailheads"]

    if len(filter_ids) != counts["filter_island"]:
        fail("wrong number of filter islands")
    if len(observation_ids) != counts["observation_point"]:
        fail("wrong number of observation points")
    if len(trailhead_ids) != counts["trailhead"]:
        fail("wrong number of trailheads")

    if len(set(filter_ids)) != len(filter_ids):
        fail("duplicate filter island IDs")
    if len(set(observation_ids)) != len(observation_ids):
        fail("duplicate observation point IDs")
    if len(set(trailhead_ids)) != len(trailhead_ids):
        fail("duplicate trailhead IDs")

    for site_id in filter_ids:
        if site_id not in all_ids["filter_island"]:
            fail(f"unknown filter island site ID: {site_id}")
        if site_id not in legal_ids["filter_island"]:
            fail(f"illegal filter island site ID: {site_id}")
    for site_id in observation_ids:
        if site_id not in all_ids["observation_point"]:
            fail(f"unknown observation point site ID: {site_id}")
        if site_id not in legal_ids["observation_point"]:
            fail(f"illegal observation point site ID: {site_id}")
    for site_id in trailhead_ids:
        if site_id not in all_ids["trailhead"]:
            fail(f"unknown trailhead site ID: {site_id}")
        if site_id not in legal_ids["trailhead"]:
            fail(f"illegal trailhead site ID: {site_id}")

    normalized = {
        "filter_island": tuple(filter_ids),
        "observation_point": tuple(observation_ids),
        "trailhead": tuple(trailhead_ids),
    }

    if not same_type_ok("filter_island", normalized["filter_island"], scenario, coord_maps):
        fail("filter islands violate same-type interference")
    if not same_type_ok("observation_point", normalized["observation_point"], scenario, coord_maps):
        fail("observation points violate same-type interference")
    if not same_type_ok("trailhead", normalized["trailhead"], scenario, coord_maps):
        fail("trailheads violate same-type interference")
    if not cross_type_ok(normalized, scenario, coord_maps):
        fail("cross-type interference violated")

    cluster_scores, synergy, total_score = evaluate(normalized, scenario, coord_maps)

    expected_cluster_ids = {cluster["id"] for cluster in scenario["habitat_clusters"]}
    if set(solution["cluster_scores"]) != expected_cluster_ids:
        fail("cluster_scores keys do not match habitat clusters")

    if solution["cluster_scores"] != cluster_scores:
        fail("cluster_scores do not match recomputed values")
    if solution["facility_synergy"] != synergy:
        fail("facility_synergy does not match recomputed values")
    if solution["total_score"] != total_score:
        fail("total_score does not match recomputed total")

    best_total = optimal_total(scenario, legal_ids, coord_maps)
    score = total_score / best_total if best_total > 0 else 0.0
    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(str(score))

    if total_score != best_total:
        fail(f"submitted total_score {total_score} != optimal {best_total}")

    print("wetland_restoration_layout verification passed")


if __name__ == "__main__":
    try:
        main()
    except AssertionError:
        raise
