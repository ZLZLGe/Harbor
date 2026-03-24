#!/bin/bash
set -euo pipefail

pip install --no-cache-dir git+https://github.com/AI4EPS/GaMMA.git@f6b1ac7680f50bcc7d5d3928361ba02a7df0f523

python3 <<'PY'
import json
import math

import pandas as pd
from gamma.utils import association, estimate_eps

PICKS_PATH = "/root/data/swarm_picks.csv"
STATIONS_PATH = "/root/data/volcano_stations.csv"
OUTPUT_PATH = "/root/volcano_swarm_events.geojson"
VP = 5.4
VS = VP / 1.78
KM_PER_DEG_LAT = 111.32


def local_projection(longitudes: pd.Series, latitudes: pd.Series):
    lon0 = longitudes.mean()
    lat0 = latitudes.mean()
    km_per_deg_lon = KM_PER_DEG_LAT * math.cos(math.radians(lat0))
    x = (longitudes - lon0) * km_per_deg_lon
    y = (latitudes - lat0) * KM_PER_DEG_LAT
    return lon0, lat0, km_per_deg_lon, x, y


picks = pd.read_csv(PICKS_PATH)
picks["timestamp"] = pd.to_datetime(picks["timestamp"])
picks["type"] = picks["type"].str.lower()

stations = pd.read_csv(STATIONS_PATH)
lon0, lat0, km_per_deg_lon, x, y = local_projection(
    stations["longitude"], stations["latitude"]
)
stations["x(km)"] = x
stations["y(km)"] = y
stations["z(km)"] = -stations["elevation_m"] / 1000.0

xmin = stations["x(km)"].min() - 8.0
xmax = stations["x(km)"].max() + 8.0
ymin = stations["y(km)"].min() - 8.0
ymax = stations["y(km)"].max() + 8.0
zmin = 0.0
zmax = 8.0

config = {
    "dims": ["x(km)", "y(km)", "z(km)"],
    "use_dbscan": True,
    "use_amplitude": False,
    "method": "BGMM",
    "oversample_factor": 5,
    "vel": {"p": VP, "s": VS},
    "dbscan_eps": estimate_eps(stations, VP),
    "dbscan_min_samples": 3,
    "min_picks_per_eq": 10,
    "min_p_picks_per_eq": 4,
    "min_s_picks_per_eq": 4,
    "min_stations": 5,
    "max_sigma11": 0.8,
    "max_sigma22": 1.0,
    "max_sigma12": 1.0,
    "bfgs_bounds": (
        (xmin, xmax),
        (ymin, ymax),
        (zmin, zmax),
        (None, None),
    ),
    "x(km)": (xmin, xmax),
    "y(km)": (ymin, ymax),
    "z(km)": (zmin, zmax),
}

events, _ = association(picks, stations, config, event_idx0=0, method=config["method"])
events = pd.DataFrame(events)
if events.empty:
    raise RuntimeError("No volcano swarm events were associated from the provided picks.")

events["time"] = pd.to_datetime(events["time"])
events["longitude"] = lon0 + events["x(km)"] / km_per_deg_lon
events["latitude"] = lat0 + events["y(km)"] / KM_PER_DEG_LAT
events["depth_km"] = events["z(km)"]
events = events.sort_values("time").reset_index(drop=True)

features = []
for _, row in events.iterrows():
    features.append(
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    round(float(row["longitude"]), 6),
                    round(float(row["latitude"]), 6),
                ],
            },
            "properties": {
                "time": row["time"].strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "depth_km": round(float(row["depth_km"]), 3),
                "num_picks": int(row["num_picks"]),
                "num_p_picks": int(row["num_p_picks"]),
                "num_s_picks": int(row["num_s_picks"]),
            },
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)
PY
