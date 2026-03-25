#!/bin/bash
set -e

TASK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export TASK_DIR

python3 <<'PY'
import os
from pathlib import Path

import numpy as np
import pandas as pd


def path_exists(path):
    try:
        return path.exists()
    except PermissionError:
        return False


def locate_input():
    candidates = [
        Path("/root/regional_grid_load_panel.tsv"),
        Path(os.environ["TASK_DIR"]) / "environment" / "regional_grid_load_panel.tsv",
        Path("regional_grid_load_panel.tsv"),
    ]
    for path in candidates:
        if path_exists(path):
            return path
    raise FileNotFoundError("regional_grid_load_panel.tsv not found")


def locate_output():
    env_path = os.environ.get("GRID_TROUGH_PATH")
    candidates = [Path("/root/grid_trough.txt")]
    if env_path:
        candidates.append(Path(env_path))

    for path in candidates:
        directory = path.parent
        if directory.exists() and os.access(directory, os.W_OK):
            return path
    raise PermissionError("No writable output path found for grid_trough.txt")


def hp_cycle(values, lamb=14400.0):
    y = np.asarray(values, dtype=float)
    n = y.shape[0]
    identity = np.eye(n)
    second_diff = np.diff(identity, n=2, axis=0)
    trend = np.linalg.solve(identity + lamb * (second_diff.T @ second_diff), y)
    return y - trend


data = pd.read_csv(locate_input(), sep="\t")

records = []
for region, frame in data.groupby("region", sort=False):
    ordered = frame.sort_values("month").copy()
    ordered["cycle"] = hp_cycle(np.log(ordered["load_gwh"].astype(float).to_numpy()))
    records.append(ordered[["region", "month", "cycle"]])

result = pd.concat(records, ignore_index=True)
trough = result.loc[result["cycle"].idxmin()]

with open(locate_output(), "w", encoding="utf-8") as handle:
    handle.write(f"region={trough['region']}\n")
    handle.write(f"month={trough['month']}\n")
PY
