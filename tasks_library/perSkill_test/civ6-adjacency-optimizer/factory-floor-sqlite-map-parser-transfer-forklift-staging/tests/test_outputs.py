#!/usr/bin/env python3

import json
import os
import sqlite3
from collections import deque
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
BRIEF_PATH = DATA_DIR / "briefing" / "transfer_request.json"
OUTPUT_PATH = OUTPUT_DIR / "forklift_staging_plan.json"


def load_layout(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    meta = {
        row["meta_key"]: row["meta_value"]
        for row in cur.execute("SELECT meta_key, meta_value FROM floor_meta")
    }
    width = int(meta["width"])
    height = int(meta["height"])

    cells = {}
    for row in cur.execute(
        "SELECT cell_ref, surface_code, lane_code, traversable FROM cell_registry ORDER BY cell_ref"
    ):
        ref = row["cell_ref"]
        cells[ref] = {
            "cell_ref": ref,
            "x": ref % width,
            "y": ref // width,
            "surface_code": row["surface_code"],
            "lane_code": row["lane_code"],
            "traversable": bool(row["traversable"]),
            "overlays": [],
        }

    for row in cur.execute(
        "SELECT cell_ref, overlay_code FROM cell_overlays ORDER BY cell_ref, overlay_code"
    ):
        cells[row["cell_ref"]]["overlays"].append(row["overlay_code"])

    assets = []
    for row in cur.execute(
        "SELECT asset_code, asset_type, anchor_ref, display_name FROM asset_registry ORDER BY asset_code"
    ):
        ref = row["anchor_ref"]
        assets.append(
            {
                "asset_code": row["asset_code"],
                "asset_type": row["asset_type"],
                "display_name": row["display_name"],
                "cell_ref": ref,
                "x": ref % width,
                "y": ref // width,
            }
        )

    conn.close()
    return {
        "meta": meta,
        "width": width,
        "height": height,
        "cells": cells,
        "assets": assets,
    }


def orthogonal_neighbors(cell, width, height, coord_to_ref, cells):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = cell["x"] + dx
        ny = cell["y"] + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield cells[coord_to_ref[(nx, ny)]]


def build_expected_plan():
    request = json.loads(BRIEF_PATH.read_text())
    layout = load_layout(DATA_DIR / request["layout_db"])
    cells = layout["cells"]
    assets = layout["assets"]
    width = layout["width"]
    height = layout["height"]
    coord_to_ref = {(cell["x"], cell["y"]): ref for ref, cell in cells.items()}

    blocked_codes = set(request["blocked_overlay_codes"])
    forbidden_codes = set(request["forbidden_overlay_codes"])
    dock_types = set(request["loading_asset_types"])
    hazard_types = set(request["hazard_asset_types"])
    candidate_lane_codes = set(request["candidate_lane_codes"])

    asset_cells = {asset["cell_ref"] for asset in assets}
    traversable_refs = {
        ref
        for ref, cell in cells.items()
        if cell["traversable"] and not (set(cell["overlays"]) & blocked_codes)
    }

    loading_docks = [asset for asset in assets if asset["asset_type"] in dock_types]
    hazards = [asset for asset in assets if asset["asset_type"] in hazard_types]

    queue = deque()
    dock_steps = {}
    nearest_dock = {}
    for dock in loading_docks:
        queue.append(dock["cell_ref"])
        dock_steps[dock["cell_ref"]] = 0
        nearest_dock[dock["cell_ref"]] = dock["asset_code"]

    while queue:
        ref = queue.popleft()
        for neighbor in orthogonal_neighbors(
            cells[ref], width, height, coord_to_ref, cells
        ):
            neighbor_ref = neighbor["cell_ref"]
            if neighbor_ref not in traversable_refs or neighbor_ref in dock_steps:
                continue
            dock_steps[neighbor_ref] = dock_steps[ref] + 1
            nearest_dock[neighbor_ref] = nearest_dock[ref]
            queue.append(neighbor_ref)

    candidates = []
    for ref, cell in cells.items():
        overlays = set(cell["overlays"])
        if not cell["traversable"]:
            continue
        if cell["lane_code"] not in candidate_lane_codes:
            continue
        if overlays & blocked_codes or overlays & forbidden_codes:
            continue
        if ref in asset_cells:
            continue
        if ref not in dock_steps or dock_steps[ref] > request["max_dock_steps"]:
            continue

        hazard_clearance = min(
            abs(cell["x"] - hazard["x"]) + abs(cell["y"] - hazard["y"])
            for hazard in hazards
        )
        if hazard_clearance < request["min_hazard_manhattan"]:
            continue

        adjacent_open_cells = 0
        for neighbor in orthogonal_neighbors(
            cell, width, height, coord_to_ref, cells
        ):
            neighbor_overlays = set(neighbor["overlays"])
            if not neighbor["traversable"]:
                continue
            if neighbor_overlays & blocked_codes or neighbor_overlays & forbidden_codes:
                continue
            if neighbor["cell_ref"] in asset_cells:
                continue
            adjacent_open_cells += 1

        candidates.append(
            {
                "cell_ref": ref,
                "x": cell["x"],
                "y": cell["y"],
                "lane_code": cell["lane_code"],
                "nearest_dock": nearest_dock[ref],
                "dock_steps": dock_steps[ref],
                "hazard_clearance": hazard_clearance,
                "adjacent_open_cells": adjacent_open_cells,
                "overlays": cell["overlays"],
            }
        )

    candidates.sort(
        key=lambda item: (
            item["dock_steps"],
            -item["hazard_clearance"],
            -item["adjacent_open_cells"],
            item["cell_ref"],
        )
    )

    forbidden_cells = [
        {
            "cell_ref": cell["cell_ref"],
            "x": cell["x"],
            "y": cell["y"],
            "overlays": cell["overlays"],
        }
        for cell in cells.values()
        if set(cell["overlays"]) & forbidden_codes
    ]

    return {
        "layout": {
            "floor_name": layout["meta"]["floor_name"],
            "width": width,
            "height": height,
            "cell_size_m": float(layout["meta"]["cell_size_m"]),
        },
        "rules": {
            "candidate_lane_codes": request["candidate_lane_codes"],
            "max_dock_steps": request["max_dock_steps"],
            "min_hazard_manhattan": request["min_hazard_manhattan"],
            "shortlist_size": request["shortlist_size"],
        },
        "summary": {
            "traversable_cells": sum(1 for cell in cells.values() if cell["traversable"]),
            "candidate_lane_cells": sum(
                1 for cell in cells.values() if cell["lane_code"] in candidate_lane_codes
            ),
            "blocked_cells": sum(
                1 for cell in cells.values() if set(cell["overlays"]) & blocked_codes
            ),
            "forbidden_cells": len(forbidden_cells),
            "loading_docks": len(loading_docks),
            "hazard_sources": len(hazards),
            "valid_candidates": len(candidates),
        },
        "loading_docks": loading_docks,
        "hazards": hazards,
        "forbidden_cells": forbidden_cells,
        "candidates": candidates[: request["shortlist_size"]],
        "recommended_cell": candidates[0],
    }


def load_output():
    with OUTPUT_PATH.open() as f:
        return json.load(f)


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_output_is_json_object():
    data = load_output()
    assert isinstance(data, dict), "output must be a JSON object"


def test_top_level_keys():
    data = load_output()
    expected_keys = {
        "layout",
        "rules",
        "summary",
        "loading_docks",
        "hazards",
        "forbidden_cells",
        "candidates",
        "recommended_cell",
    }
    assert set(data.keys()) == expected_keys


def test_summary_matches_expected():
    actual = load_output()
    expected = build_expected_plan()
    assert actual["layout"] == expected["layout"]
    assert actual["rules"] == expected["rules"]
    assert actual["summary"] == expected["summary"]


def test_asset_sections_match_expected():
    actual = load_output()
    expected = build_expected_plan()
    assert actual["loading_docks"] == expected["loading_docks"]
    assert actual["hazards"] == expected["hazards"]
    assert actual["forbidden_cells"] == expected["forbidden_cells"]


def test_candidates_match_expected_order_and_values():
    actual = load_output()
    expected = build_expected_plan()
    assert actual["candidates"] == expected["candidates"]
    assert len(actual["candidates"]) <= actual["rules"]["shortlist_size"]


def test_recommended_cell_matches_first_candidate():
    actual = load_output()
    assert actual["candidates"], "candidates must not be empty"
    assert actual["recommended_cell"] == actual["candidates"][0]


if __name__ == "__main__":
    test_output_file_exists()
    test_output_is_json_object()
    test_top_level_keys()
    test_summary_matches_expected()
    test_asset_sections_match_expected()
    test_candidates_match_expected_order_and_values()
    test_recommended_cell_matches_first_candidate()
    print("All checks passed.")
