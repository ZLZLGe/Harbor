#!/bin/bash

python3 <<'PY'
import os
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.environ.get("BOOTSTRAP_DATA_DIR", "/root/bootstrap_data"))
OUTPUT_FILE = Path(os.environ.get("BOOTSTRAP_OUTPUT_FILE", "/root/bootstrap_events.csv"))


def load_candidate(name: str) -> pd.DataFrame:
    frame = pd.read_csv(DATA_DIR / f"candidate_catalog_{name}.csv")
    frame["time"] = pd.to_datetime(frame["time"])
    return frame


def score_candidate(frame: pd.DataFrame, review_windows: pd.DataFrame) -> tuple[int, int, float]:
    earthquake_hits = 0
    noise_hits = 0
    total_support = 0.0
    for row in review_windows.itertuples(index=False):
        start = pd.Timestamp(row.window_start)
        end = pd.Timestamp(row.window_end)
        in_window = frame[(frame["time"] >= start) & (frame["time"] <= end)]
        if row.manual_label == "earthquake":
            if not in_window.empty:
                earthquake_hits += 1
                total_support += in_window["supporting_stations"].max()
        elif not in_window.empty:
            noise_hits += 1
    return earthquake_hits, noise_hits, total_support


def deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(
        by=["time", "supporting_stations", "mean_pick_score"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    kept = []
    for row in ordered.itertuples(index=False):
        row_time = row.time
        if not kept:
            kept.append(row)
            continue
        previous = kept[-1]
        if (row_time - previous.time).total_seconds() <= 4:
            better = (
                row.supporting_stations > previous.supporting_stations
                or (
                    row.supporting_stations == previous.supporting_stations
                    and row.mean_pick_score > previous.mean_pick_score
                )
            )
            if better:
                kept[-1] = row
        else:
            kept.append(row)
    result = pd.DataFrame(kept)
    return result.sort_values("time").reset_index(drop=True)


review = pd.read_csv(DATA_DIR / "manual_review_windows.csv")

candidates = {
    "sta_lta": load_candidate("sta_lta"),
    "deep_learning": load_candidate("deep_learning"),
    "template_matching": load_candidate("template_matching"),
}

scores = {name: score_candidate(frame, review) for name, frame in candidates.items()}

best_name = max(
    scores,
    key=lambda name: (scores[name][0], -scores[name][1], scores[name][2]),
)

final_catalog = deduplicate(candidates[best_name]).copy()
final_catalog["time"] = final_catalog["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
final_catalog["method_family"] = best_name
final_catalog = final_catalog[["time", "supporting_stations", "mean_pick_score", "method_family"]]

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
final_catalog.to_csv(OUTPUT_FILE, index=False)
PY
