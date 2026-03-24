#!/usr/bin/env python3

import json
import os
import sqlite3
from itertools import combinations
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
BRIEF_PATH = DATA_DIR / "briefing" / "sensor_request.json"
OUTPUT_PATH = OUTPUT_DIR / "sensor_siting_plan.json"


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}\nACTUAL: {actual}\nEXPECTED: {expected}")


def load_request():
    return json.loads(BRIEF_PATH.read_text())


def load_reserve(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    meta = {
        row["meta_key"]: row["meta_value"]
        for row in cur.execute(
            "SELECT meta_key, meta_value FROM reserve_meta ORDER BY meta_key"
        )
    }
    width = int(meta["width"])
    height = int(meta["height"])

    overlays = {}
    for row in cur.execute(
        "SELECT parcel_id, overlay_code FROM parcel_overlays ORDER BY parcel_id, overlay_code"
    ):
        overlays.setdefault(row["parcel_id"], []).append(row["overlay_code"])

    waterway_parcels = {
        row["parcel_id"]
        for row in cur.execute("SELECT DISTINCT parcel_id FROM parcel_waterways")
    }

    parcels = {}
    for row in cur.execute(
        """
        SELECT parcel_id, land_cover, access_code, installable
        FROM parcel_registry
        ORDER BY parcel_id
        """
    ):
        parcel_id = row["parcel_id"]
        parcels[parcel_id] = {
            "parcel_id": parcel_id,
            "x": parcel_id % width,
            "y": parcel_id // width,
            "land_cover": row["land_cover"],
            "access_code": row["access_code"],
            "installable": bool(row["installable"]),
            "overlay_codes": overlays.get(parcel_id, []),
        }

    habitats = [dict(row) for row in cur.execute(
        """
        SELECT habitat_code, parcel_id, habitat_type, priority_tier, label
        FROM habitat_registry
        ORDER BY habitat_code
        """
    )]
    sites = [dict(row) for row in cur.execute(
        """
        SELECT site_code, parcel_id, site_label, install_cost
        FROM sensor_site_registry
        ORDER BY site_code
        """
    )]

    conn.close()
    return {
        "meta": meta,
        "width": width,
        "height": height,
        "waterway_parcels": waterway_parcels,
        "parcels": parcels,
        "habitats": habitats,
        "sites": sites,
    }


def orthogonal_neighbor_ids(parcel, width, height):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = parcel["x"] + dx
        ny = parcel["y"] + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield ny * width + nx


def bank_contacts(parcel, width, height, waterway_parcels):
    count = 1 if parcel["parcel_id"] in waterway_parcels else 0
    count += sum(
        1
        for neighbor_id in orthogonal_neighbor_ids(parcel, width, height)
        if neighbor_id in waterway_parcels
    )
    return count


def manhattan(a, b):
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])


def build_expected_plan():
    request = load_request()
    reserve = load_reserve(DATA_DIR / request["layout_db"])
    parcels = reserve["parcels"]
    width = reserve["width"]
    height = reserve["height"]
    blocked_codes = set(request["blocked_overlay_codes"])
    target_types = set(request["target_habitat_types"])
    priority_weights = request["priority_weights"]

    key_habitats = []
    habitat_by_code = {}
    habitat_parcel_ids = set()
    for habitat in reserve["habitats"]:
        if habitat["habitat_type"] not in target_types:
            continue
        parcel = parcels[habitat["parcel_id"]]
        item = {
            "habitat_code": habitat["habitat_code"],
            "parcel_id": habitat["parcel_id"],
            "x": parcel["x"],
            "y": parcel["y"],
            "label": habitat["label"],
            "habitat_type": habitat["habitat_type"],
            "priority_tier": habitat["priority_tier"],
            "priority_weight": priority_weights[habitat["priority_tier"]],
            "waterway_contacts": bank_contacts(
                parcel, width, height, reserve["waterway_parcels"]
            ),
        }
        key_habitats.append(item)
        habitat_by_code[item["habitat_code"]] = item
        habitat_parcel_ids.add(item["parcel_id"])

    no_entry_zones = []
    for parcel in parcels.values():
        overlay_codes = [
            code for code in parcel["overlay_codes"] if code in blocked_codes
        ]
        if overlay_codes:
            no_entry_zones.append(
                {
                    "parcel_id": parcel["parcel_id"],
                    "x": parcel["x"],
                    "y": parcel["y"],
                    "overlay_codes": overlay_codes,
                }
            )
    no_entry_zones.sort(key=lambda item: item["parcel_id"])

    valid_sites = []
    for site in reserve["sites"]:
        parcel = parcels[site["parcel_id"]]
        if not parcel["installable"]:
            continue
        if site["parcel_id"] in habitat_parcel_ids:
            continue
        if set(parcel["overlay_codes"]) & blocked_codes:
            continue
        contact_count = bank_contacts(parcel, width, height, reserve["waterway_parcels"])
        if contact_count < request["min_bank_contacts"]:
            continue

        coverable = [
            habitat["habitat_code"]
            for habitat in key_habitats
            if manhattan(parcel, habitat) <= request["sensor_radius"]
        ]
        coverable.sort()
        valid_sites.append(
            {
                "site_code": site["site_code"],
                "site_label": site["site_label"],
                "parcel_id": parcel["parcel_id"],
                "x": parcel["x"],
                "y": parcel["y"],
                "access_code": parcel["access_code"],
                "install_cost": site["install_cost"],
                "bank_contacts": contact_count,
                "coverable_habitat_codes": coverable,
                "coverable_habitat_count": len(coverable),
                "coverable_priority_weight": sum(
                    habitat_by_code[code]["priority_weight"] for code in coverable
                ),
            }
        )

    valid_sites.sort(
        key=lambda item: (
            -item["coverable_priority_weight"],
            -item["coverable_habitat_count"],
            item["install_cost"],
            -item["bank_contacts"],
            item["site_code"],
        )
    )

    best_combo = None
    for size in range(1, request["max_sites"] + 1):
        for combo in combinations(valid_sites, size):
            total_cost = sum(item["install_cost"] for item in combo)
            if total_cost > request["budget_cap"]:
                continue
            covered_codes = sorted(
                {code for item in combo for code in item["coverable_habitat_codes"]}
            )
            covered_weight = sum(
                habitat_by_code[code]["priority_weight"] for code in covered_codes
            )
            decision_key = (
                -covered_weight,
                -len(covered_codes),
                total_cost,
                tuple(sorted(item["site_code"] for item in combo)),
            )
            if best_combo is None or decision_key < best_combo[0]:
                best_combo = (decision_key, combo, covered_codes, covered_weight, total_cost)

    if best_combo is None:
        raise AssertionError("no feasible deployment plan found from fixture data")

    _, selected_combo, covered_codes, covered_weight, total_cost = best_combo
    selected_sites = sorted(selected_combo, key=lambda item: item["site_code"])
    uncovered_codes = sorted(
        code for code in habitat_by_code if code not in set(covered_codes)
    )

    return {
        "reserve": {
            "reserve_name": reserve["meta"]["reserve_name"],
            "width": width,
            "height": height,
            "cell_size_m": int(reserve["meta"]["cell_size_m"]),
        },
        "rules": {
            "target_habitat_types": request["target_habitat_types"],
            "sensor_radius": request["sensor_radius"],
            "min_bank_contacts": request["min_bank_contacts"],
            "budget_cap": request["budget_cap"],
            "max_sites": request["max_sites"],
            "shortlist_size": request["shortlist_size"],
        },
        "summary": {
            "waterway_parcels": len(reserve["waterway_parcels"]),
            "key_habitats": len(key_habitats),
            "candidate_sites": len(valid_sites),
            "shortlisted_sites": min(len(valid_sites), request["shortlist_size"]),
            "selected_sites": len(selected_sites),
            "covered_habitats": len(covered_codes),
            "covered_priority_weight": covered_weight,
            "budget_used": total_cost,
        },
        "key_habitats": key_habitats,
        "no_entry_zones": no_entry_zones,
        "candidate_sites": valid_sites[: request["shortlist_size"]],
        "deployment_plan": {
            "selected_site_codes": [item["site_code"] for item in selected_sites],
            "total_install_cost": total_cost,
            "covered_habitat_codes": covered_codes,
            "uncovered_habitat_codes": uncovered_codes,
            "sensors": [
                {
                    "site_code": item["site_code"],
                    "site_label": item["site_label"],
                    "parcel_id": item["parcel_id"],
                    "x": item["x"],
                    "y": item["y"],
                    "install_cost": item["install_cost"],
                    "bank_contacts": item["bank_contacts"],
                    "covered_habitat_codes": item["coverable_habitat_codes"],
                }
                for item in selected_sites
            ],
        },
    }


def load_output():
    if not OUTPUT_PATH.exists():
        raise AssertionError(f"missing output file: {OUTPUT_PATH}")
    with OUTPUT_PATH.open() as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise AssertionError("output must be a JSON object")
    return data


def main():
    expected = build_expected_plan()
    actual = load_output()

    assert_equal(actual.get("reserve"), expected["reserve"], "reserve block mismatch")
    assert_equal(actual.get("rules"), expected["rules"], "rules block mismatch")
    assert_equal(actual.get("summary"), expected["summary"], "summary mismatch")
    assert_equal(actual.get("key_habitats"), expected["key_habitats"], "key_habitats mismatch")
    assert_equal(actual.get("no_entry_zones"), expected["no_entry_zones"], "no_entry_zones mismatch")
    assert_equal(actual.get("candidate_sites"), expected["candidate_sites"], "candidate_sites mismatch")

    deployment = actual.get("deployment_plan")
    expected_deployment = expected["deployment_plan"]
    assert isinstance(deployment, dict), "deployment_plan must be an object"
    assert_equal(
        deployment.get("selected_site_codes"),
        expected_deployment["selected_site_codes"],
        "selected_site_codes mismatch",
    )
    assert_equal(
        deployment.get("total_install_cost"),
        expected_deployment["total_install_cost"],
        "total_install_cost mismatch",
    )
    assert_equal(
        deployment.get("covered_habitat_codes"),
        expected_deployment["covered_habitat_codes"],
        "covered_habitat_codes mismatch",
    )
    assert_equal(
        deployment.get("uncovered_habitat_codes"),
        expected_deployment["uncovered_habitat_codes"],
        "uncovered_habitat_codes mismatch",
    )
    assert_equal(
        deployment.get("sensors"),
        expected_deployment["sensors"],
        "deployment sensors mismatch",
    )

    summary = actual["summary"]
    assert_equal(
        summary["selected_sites"],
        len(deployment["selected_site_codes"]),
        "summary.selected_sites inconsistent with deployment_plan",
    )
    assert_equal(
        summary["budget_used"],
        deployment["total_install_cost"],
        "summary.budget_used inconsistent with deployment_plan",
    )
    assert_equal(
        summary["covered_habitats"],
        len(deployment["covered_habitat_codes"]),
        "summary.covered_habitats inconsistent with deployment_plan",
    )
    print("sensor_siting_plan.json validated")


if __name__ == "__main__":
    main()
