#!/usr/bin/env python3

import json
import os
import sqlite3
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output"))
BRIEF_PATH = DATA_DIR / "briefing" / "settlement_brief.json"
OUTPUT_PATH = OUTPUT_DIR / "settlement_dossier.json"


def load_map(map_path: Path):
    conn = sqlite3.connect(map_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    map_row = cur.execute("SELECT Width, Height, WrapX FROM Map").fetchone()
    metadata = {
        row["Name"]: row["Value"]
        for row in cur.execute("SELECT Name, Value FROM MetaData")
    }

    plots = {}
    for row in cur.execute("SELECT ID, TerrainType, IsImpassable FROM Plots"):
        plot_id = row["ID"]
        plots[plot_id] = {
            "plot_id": plot_id,
            "x": plot_id % map_row["Width"],
            "y": plot_id // map_row["Width"],
            "terrain": row["TerrainType"],
            "impassable": bool(row["IsImpassable"]),
            "feature": None,
            "river_edges": {"ne": False, "w": False, "nw": False},
        }

    for row in cur.execute("SELECT ID, FeatureType FROM PlotFeatures"):
        if row["ID"] in plots:
            plots[row["ID"]]["feature"] = row["FeatureType"]

    for row in cur.execute(
        "SELECT ID, IsNEOfRiver, IsWOfRiver, IsNWOfRiver FROM PlotRivers"
    ):
        if row["ID"] in plots:
            plots[row["ID"]]["river_edges"] = {
                "ne": bool(row["IsNEOfRiver"]),
                "w": bool(row["IsWOfRiver"]),
                "nw": bool(row["IsNWOfRiver"]),
            }

    conn.close()
    return {
        "width": map_row["Width"],
        "height": map_row["Height"],
        "wrap_x": bool(map_row["WrapX"]),
        "map_name": metadata.get("DisplayName", map_path.stem),
        "plots": plots,
    }


def neighbors(x: int, y: int, width: int, height: int, wrap_x: bool):
    if y % 2 == 1:
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
    else:
        directions = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]

    result = []
    for dx, dy in directions:
        nx = x + dx
        ny = y + dy
        if wrap_x:
            nx %= width
        if 0 <= ny < height:
            result.append((nx, ny))
    return result


def offset_to_cube(x: int, y: int):
    cx = x - (y - (y & 1)) // 2
    cz = y
    cy = -cx - cz
    return cx, cy, cz


def hex_distance(a, b):
    a_cube = offset_to_cube(*a)
    b_cube = offset_to_cube(*b)
    return sum(abs(a_cube[i] - b_cube[i]) for i in range(3)) // 2


def is_land(plot):
    return plot["terrain"] not in ("TERRAIN_OCEAN", "TERRAIN_COAST")


def is_settleable(plot):
    return is_land(plot) and not plot["impassable"]


def has_river(plot):
    return any(plot["river_edges"].values())


def build_expected_dossier():
    brief = json.loads(BRIEF_PATH.read_text())
    map_info = load_map(DATA_DIR / brief["map_file"])
    plots = map_info["plots"]
    coord_to_plot = {(plot["x"], plot["y"]): plot for plot in plots.values()}
    radius = brief["search_radius"]
    shortlist_size = brief["shortlist_size"]
    weights = brief["planning_score_weights"]
    feature_signal_bucket = set(brief["feature_buckets"]["feature_signal"])
    campus_specials = set(brief["feature_buckets"]["campus_specials"])
    campus_adjacent_bonus = set(brief["feature_buckets"]["campus_adjacent_bonus"])

    def tiles_in_range(center_xy):
        result = []
        for plot in plots.values():
            distance = hex_distance(center_xy, (plot["x"], plot["y"]))
            if 0 < distance <= radius:
                result.append((distance, plot))
        return result

    def score_center(plot):
        ring = [item[1] for item in tiles_in_range((plot["x"], plot["y"]))]
        campus_signal = sum(
            1
            for tile in ring
            if tile["terrain"].endswith("_MOUNTAIN") or tile["feature"] in campus_specials
        )
        commercial_signal = sum(
            1 for tile in ring if is_settleable(tile) and has_river(tile)
        )
        coastal_access_signal = sum(1 for tile in ring if tile["terrain"] == "TERRAIN_COAST")
        feature_signal = sum(
            1 for tile in ring if tile["feature"] in feature_signal_bucket
        )
        planning_score = (
            weights["campus_signal"] * campus_signal
            + weights["commercial_signal"] * commercial_signal
            + weights["coastal_access_signal"] * coastal_access_signal
            + weights["feature_signal"] * feature_signal
        )
        return {
            "plot": plot,
            "planning_score": planning_score,
            "score_breakdown": {
                "campus_signal": campus_signal,
                "commercial_signal": commercial_signal,
                "coastal_access_signal": coastal_access_signal,
                "feature_signal": feature_signal,
            },
        }

    centers = [score_center(plot) for plot in plots.values() if is_settleable(plot)]
    centers.sort(
        key=lambda item: (
            -item["planning_score"],
            -item["score_breakdown"]["campus_signal"],
            -item["score_breakdown"]["commercial_signal"],
            item["plot"]["plot_id"],
        )
    )
    best = centers[0]
    best_plot = best["plot"]
    ring = tiles_in_range((best_plot["x"], best_plot["y"]))
    ring_plots = [item[1] for item in ring]

    campus_sites = []
    commercial_sites = []
    coast_tiles = []

    for distance, plot in ring:
        adjacent = [
            coord_to_plot[coord]
            for coord in neighbors(
                plot["x"], plot["y"], map_info["width"], map_info["height"], map_info["wrap_x"]
            )
            if coord in coord_to_plot
        ]
        if is_settleable(plot):
            adjacent_mountains = sum(
                1 for tile in adjacent if tile["terrain"].endswith("_MOUNTAIN")
            )
            adjacent_geothermal = sum(
                1 for tile in adjacent if tile["feature"] in campus_specials
            )
            adjacent_reefs = sum(
                1 for tile in adjacent if tile["feature"] in campus_adjacent_bonus
            )
            campus_sites.append(
                {
                    "plot_id": plot["plot_id"],
                    "x": plot["x"],
                    "y": plot["y"],
                    "score": 2 * adjacent_mountains + 2 * adjacent_geothermal + adjacent_reefs,
                    "adjacent_mountains": adjacent_mountains,
                    "adjacent_geothermal": adjacent_geothermal,
                    "adjacent_reefs": adjacent_reefs,
                }
            )

            adjacent_coast_tiles = sum(
                1 for tile in adjacent if tile["terrain"] == "TERRAIN_COAST"
            )
            commercial_sites.append(
                {
                    "plot_id": plot["plot_id"],
                    "x": plot["x"],
                    "y": plot["y"],
                    "score": (2 if has_river(plot) else 0) + adjacent_coast_tiles,
                    "river_touched": has_river(plot),
                    "adjacent_coast_tiles": adjacent_coast_tiles,
                }
            )

        if plot["terrain"] == "TERRAIN_COAST":
            coast_tiles.append(
                {
                    "plot_id": plot["plot_id"],
                    "x": plot["x"],
                    "y": plot["y"],
                    "distance": distance,
                }
            )

    campus_sites.sort(key=lambda item: (-item["score"], item["plot_id"]))
    commercial_sites.sort(key=lambda item: (-item["score"], item["plot_id"]))
    coast_tiles.sort(key=lambda item: (item["distance"], item["plot_id"]))

    return {
        "map": {
            "width": map_info["width"],
            "height": map_info["height"],
            "wrap_x": map_info["wrap_x"],
            "map_name": map_info["map_name"],
        },
        "best_city_center": {
            "plot_id": best_plot["plot_id"],
            "x": best_plot["x"],
            "y": best_plot["y"],
            "planning_score": best["planning_score"],
            "score_breakdown": best["score_breakdown"],
        },
        "radius_3_summary": {
            "total_tiles": len(ring_plots),
            "land_tiles": sum(1 for plot in ring_plots if is_land(plot)),
            "coast_tiles": sum(1 for plot in ring_plots if plot["terrain"] == "TERRAIN_COAST"),
            "ocean_tiles": sum(1 for plot in ring_plots if plot["terrain"] == "TERRAIN_OCEAN"),
            "mountain_tiles": sum(
                1 for plot in ring_plots if plot["terrain"].endswith("_MOUNTAIN")
            ),
            "river_land_tiles": sum(
                1 for plot in ring_plots if is_settleable(plot) and has_river(plot)
            ),
            "geothermal_tiles": sum(
                1 for plot in ring_plots if plot["feature"] in campus_specials
            ),
            "forest_or_jungle_tiles": sum(
                1
                for plot in ring_plots
                if plot["feature"] in {"FEATURE_FOREST", "FEATURE_JUNGLE"}
            ),
            "floodplains_tiles": sum(
                1 for plot in ring_plots if plot["feature"] == "FEATURE_FLOODPLAINS_PLAINS"
            ),
        },
        "district_shortlist": {
            "campus": campus_sites[:shortlist_size],
            "commercial_hub": commercial_sites[:shortlist_size],
        },
        "harbor_access": {
            "coast_tiles_in_range": sum(
                1 for plot in ring_plots if plot["terrain"] == "TERRAIN_COAST"
            ),
            "nearest_coast_tiles": coast_tiles[:shortlist_size],
        },
    }


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_output_is_valid_json():
    with OUTPUT_PATH.open() as f:
        data = json.load(f)
    assert isinstance(data, dict), "output must be a JSON object"


def test_output_matches_expected_dossier():
    expected = build_expected_dossier()
    with OUTPUT_PATH.open() as f:
        actual = json.load(f)
    assert actual == expected


if __name__ == "__main__":
    test_output_file_exists()
    test_output_is_valid_json()
    test_output_matches_expected_dossier()
    print("All checks passed.")
