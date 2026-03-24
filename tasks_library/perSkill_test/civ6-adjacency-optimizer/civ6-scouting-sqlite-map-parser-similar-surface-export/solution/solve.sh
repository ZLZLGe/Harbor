#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
import sqlite3
from pathlib import Path

REQUEST_FILE = Path(os.environ.get("TASK_REQUEST_FILE", "/data/request/surface_request.json"))
OUTPUT_FILE = Path(os.environ.get("TASK_OUTPUT_FILE", "/output/civ6_district_surface.json"))


def hex_distance(x1, y1, x2, y2):
    def offset_to_cube(col, row):
        cx = col - (row - (row & 1)) // 2
        cz = row
        cy = -cx - cz
        return cx, cy, cz

    cx1, cy1, cz1 = offset_to_cube(x1, y1)
    cx2, cy2, cz2 = offset_to_cube(x2, y2)
    return (abs(cx1 - cx2) + abs(cy1 - cy2) + abs(cz1 - cz2)) // 2


def load_request():
    with REQUEST_FILE.open() as handle:
        return json.load(handle)


def table_exists(cur, table_name):
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def parse_map(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("SELECT Width, Height FROM Map LIMIT 1").fetchone()
    width, height = row["Width"], row["Height"]

    plots = []
    for row in cur.execute("SELECT * FROM Plots ORDER BY ID"):
        plot_id = row["ID"]
        x = plot_id % width
        y = plot_id // width
        terrain_type = row["TerrainType"]
        plots.append(
            {
                "plot_id": plot_id,
                "x": x,
                "y": y,
                "terrain_type": terrain_type,
                "is_hills": terrain_type.endswith("_HILLS"),
                "feature_type": None,
                "is_water": terrain_type in {"TERRAIN_COAST", "TERRAIN_OCEAN", "TERRAIN_LAKE"},
                "is_mountain": terrain_type.endswith("_MOUNTAIN"),
                "river_edges": [],
                "resource_type": None,
                "resource_count": None,
            }
        )

    plots_by_id = {plot["plot_id"]: plot for plot in plots}

    if table_exists(cur, "PlotFeatures"):
        for row in cur.execute("SELECT ID, FeatureType FROM PlotFeatures ORDER BY ID"):
            plots_by_id[row["ID"]]["feature_type"] = row["FeatureType"]

    if table_exists(cur, "PlotResources"):
        for row in cur.execute("SELECT ID, ResourceType, ResourceCount FROM PlotResources ORDER BY ID"):
            plot = plots_by_id[row["ID"]]
            plot["resource_type"] = row["ResourceType"]
            plot["resource_count"] = row["ResourceCount"]

    if table_exists(cur, "PlotRivers"):
        for row in cur.execute("SELECT * FROM PlotRivers ORDER BY ID"):
            river_edges = []
            if row["EFlowDirection"] != -1:
                river_edges.append(0)
            if row["IsNEOfRiver"]:
                river_edges.append(1)
            if row["IsNWOfRiver"]:
                river_edges.append(2)
            if row["IsWOfRiver"]:
                river_edges.append(3)
            if row["SWFlowDirection"] != -1:
                river_edges.append(4)
            if row["SEFlowDirection"] != -1:
                river_edges.append(5)
            plots_by_id[row["ID"]]["river_edges"] = sorted(river_edges)

    conn.close()
    return width, height, plots


def compute_blockers(plot):
    blockers = []
    if plot["is_water"]:
        blockers.append("water")
    if plot["is_mountain"]:
        blockers.append("mountain")
    if plot["feature_type"] == "FEATURE_GEOTHERMAL_FISSURE":
        blockers.append("geothermal_fissure")
    if plot["resource_type"] is not None:
        blockers.append("resource_present")
    return blockers


def build_output():
    request = load_request()
    width, height, plot_items = parse_map(request["map_file"])
    city_center = request["candidate_city_center"]
    ring_plots = []

    for plot in plot_items:
        distance = hex_distance(plot["x"], plot["y"], city_center[0], city_center[1])
        if distance == 0 or distance > request["ring_radius"]:
            continue
        blockers = compute_blockers(plot)
        ring_plots.append(
            {
                "plot_id": plot["plot_id"],
                "x": plot["x"],
                "y": plot["y"],
                "distance": distance,
                "blockers": blockers,
                "is_general_land_district_candidate": not blockers,
            }
        )

    candidate_plot_count = sum(1 for plot in ring_plots if plot["is_general_land_district_candidate"])

    return {
        "map": {
            "width": width,
            "height": height,
            "plot_count": len(plot_items),
        },
        "request": request,
        "plots": plot_items,
        "city_center_surface": {
            "city_center": request["candidate_city_center"],
            "ring_radius": request["ring_radius"],
            "ring_plots": ring_plots,
            "summary": {
                "ring_plot_count": len(ring_plots),
                "candidate_plot_count": candidate_plot_count,
                "blocked_plot_count": len(ring_plots) - candidate_plot_count,
            },
        },
    }


OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_FILE.open("w") as handle:
    json.dump(build_output(), handle, indent=2)
PY
