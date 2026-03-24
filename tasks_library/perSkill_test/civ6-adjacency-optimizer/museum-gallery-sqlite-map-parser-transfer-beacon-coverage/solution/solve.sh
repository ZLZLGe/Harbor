#!/bin/bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"

python3 - <<'PY'
import json
import os
import sqlite3
from collections import deque
from itertools import combinations
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
BRIEF_PATH = DATA_DIR / "briefing" / "beacon_request.json"
OUTPUT_PATH = OUTPUT_DIR / "gallery_beacon_plan.json"


def load_gallery(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    meta = {
        row["meta_key"]: row["meta_value"]
        for row in cur.execute("SELECT meta_key, meta_value FROM gallery_meta ORDER BY meta_key")
    }

    rooms = {}
    for row in cur.execute(
        "SELECT room_id, room_code, room_name, sort_index FROM room_registry ORDER BY sort_index, room_code"
    ):
        rooms[row["room_id"]] = {
            "room_id": row["room_id"],
            "room_code": row["room_code"],
            "room_name": row["room_name"],
            "sort_index": row["sort_index"],
        }

    doors = [
        dict(row)
        for row in cur.execute(
            "SELECT door_code, room_a_id, room_b_id, visitor_access FROM door_registry ORDER BY door_code"
        )
    ]

    exhibits = [
        dict(row)
        for row in cur.execute(
            """
            SELECT exhibit_code, title, priority_tier, room_id
            FROM exhibit_registry
            ORDER BY exhibit_code
            """
        )
    ]

    feeds = {
        row["feed_code"]: dict(row)
        for row in cur.execute(
            """
            SELECT feed_code, room_id, voltage, is_live
            FROM power_feed_registry
            ORDER BY feed_code
            """
        )
    }

    mounts = [
        dict(row)
        for row in cur.execute(
            """
            SELECT mount_code, mount_label, room_id, feed_code, install_cost, is_blocked
            FROM mount_point_registry
            ORDER BY mount_code
            """
        )
    ]

    conn.close()
    return {
        "meta": meta,
        "rooms": rooms,
        "doors": doors,
        "exhibits": exhibits,
        "feeds": feeds,
        "mounts": mounts,
    }


def reachable_rooms(start_room_id, adjacency, max_hops):
    seen = {start_room_id: 0}
    queue = deque([start_room_id])
    while queue:
        room_id = queue.popleft()
        if seen[room_id] == max_hops:
            continue
        for neighbor in adjacency[room_id]:
            if neighbor in seen:
                continue
            seen[neighbor] = seen[room_id] + 1
            queue.append(neighbor)
    return set(seen)


def build_plan():
    brief = json.loads(BRIEF_PATH.read_text())
    gallery = load_gallery(DATA_DIR / brief["layout_db"])
    rooms = gallery["rooms"]
    feeds = gallery["feeds"]
    priority_tiers = set(brief["priority_tiers"])

    visitor_doors = [door for door in gallery["doors"] if door["visitor_access"] == 1]
    adjacency = {room_id: set() for room_id in rooms}
    for door in visitor_doors:
        adjacency[door["room_a_id"]].add(door["room_b_id"])
        adjacency[door["room_b_id"]].add(door["room_a_id"])

    priority_exhibits = []
    for exhibit in gallery["exhibits"]:
        if exhibit["priority_tier"] not in priority_tiers:
            continue
        room = rooms[exhibit["room_id"]]
        priority_exhibits.append(
            {
                "exhibit_code": exhibit["exhibit_code"],
                "title": exhibit["title"],
                "tier": exhibit["priority_tier"],
                "room_code": room["room_code"],
                "room_name": room["room_name"],
                "room_id": room["room_id"],
            }
        )

    valid_candidates = []
    for mount in gallery["mounts"]:
        feed = feeds[mount["feed_code"]]
        if mount["is_blocked"] != 0:
            continue
        if feed["is_live"] != 1:
            continue
        if feed["voltage"] != brief["required_voltage"]:
            continue
        coverage_room_ids = reachable_rooms(
            mount["room_id"], adjacency, brief["max_room_hops"]
        )
        covered = [
            exhibit["exhibit_code"]
            for exhibit in priority_exhibits
            if exhibit["room_id"] in coverage_room_ids
        ]
        room_codes = sorted(rooms[room_id]["room_code"] for room_id in coverage_room_ids)
        room = rooms[mount["room_id"]]
        valid_candidates.append(
            {
                "mount_code": mount["mount_code"],
                "mount_label": mount["mount_label"],
                "room_code": room["room_code"],
                "room_name": room["room_name"],
                "feed_code": mount["feed_code"],
                "install_cost": mount["install_cost"],
                "coverage_rooms": room_codes,
                "covered_exhibits": covered,
                "covered_priority_count": len(covered),
            }
        )

    valid_candidates.sort(
        key=lambda item: (
            -item["covered_priority_count"],
            item["install_cost"],
            item["mount_code"],
        )
    )

    exhibit_codes = {item["exhibit_code"] for item in priority_exhibits}
    best_selection = None
    for size in range(1, len(valid_candidates) + 1):
        for combo in combinations(valid_candidates, size):
            covered = set()
            total_cost = 0
            codes = []
            for candidate in combo:
                covered.update(candidate["covered_exhibits"])
                total_cost += candidate["install_cost"]
                codes.append(candidate["mount_code"])
            if covered != exhibit_codes:
                continue
            selection_key = (size, total_cost, tuple(sorted(codes)))
            if best_selection is None or selection_key < best_selection[0]:
                best_selection = (selection_key, combo)
        if best_selection is not None:
            break

    _, selected_combo = best_selection
    selected = sorted(selected_combo, key=lambda item: item["mount_code"])
    selected_codes = [item["mount_code"] for item in selected]

    coverage_assignments = []
    for exhibit in priority_exhibits:
        covering_codes = sorted(
            item["mount_code"]
            for item in selected
            if exhibit["exhibit_code"] in item["covered_exhibits"]
        )
        coverage_assignments.append(
            {
                "exhibit_code": exhibit["exhibit_code"],
                "mount_code": covering_codes[0],
            }
        )

    covered_priority_rooms = len({item["room_code"] for item in priority_exhibits})

    return {
        "gallery": {
            "venue_name": gallery["meta"]["venue_name"],
            "exhibition_name": gallery["meta"]["exhibition_name"],
            "room_count": len(rooms),
            "visitor_door_count": len(visitor_doors),
        },
        "rules": {
            "priority_tiers": brief["priority_tiers"],
            "required_voltage": brief["required_voltage"],
            "max_room_hops": brief["max_room_hops"],
            "shortlist_size": brief["shortlist_size"],
        },
        "summary": {
            "priority_exhibits": len(priority_exhibits),
            "valid_mount_points": len(valid_candidates),
            "selected_beacons": len(selected),
            "priority_rooms_covered": covered_priority_rooms,
        },
        "priority_exhibits": [
            {
                "exhibit_code": item["exhibit_code"],
                "title": item["title"],
                "tier": item["tier"],
                "room_code": item["room_code"],
                "room_name": item["room_name"],
            }
            for item in priority_exhibits
        ],
        "candidate_beacons": valid_candidates[: brief["shortlist_size"]],
        "deployment_plan": {
            "selected_mount_codes": selected_codes,
            "total_install_cost": sum(item["install_cost"] for item in selected),
            "beacons": [
                {
                    "mount_code": item["mount_code"],
                    "mount_label": item["mount_label"],
                    "room_code": item["room_code"],
                    "room_name": item["room_name"],
                    "feed_code": item["feed_code"],
                    "install_cost": item["install_cost"],
                    "coverage_rooms": item["coverage_rooms"],
                    "covered_exhibits": item["covered_exhibits"],
                }
                for item in selected
            ],
            "coverage_assignments": coverage_assignments,
        },
    }


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
plan = build_plan()
OUTPUT_PATH.write_text(json.dumps(plan, indent=2), encoding="utf-8")
print(f"written {OUTPUT_PATH}")
PY
