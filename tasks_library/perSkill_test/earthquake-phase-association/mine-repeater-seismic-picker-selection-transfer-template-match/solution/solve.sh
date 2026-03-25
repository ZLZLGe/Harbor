#!/bin/bash

set -euo pipefail

python3 <<'PY'
from pathlib import Path

import pandas as pd


DATA_DIR = Path("/root/mine_inputs")
OUTPUT_FILE = Path("/root/mine_repeater_events.csv")
METHOD_FILES = {
    "sta_lta": "candidate_repeater_sta_lta.csv",
    "deep_learning": "candidate_repeater_deep_learning.csv",
    "template_matching": "candidate_repeater_template_matching.csv",
}


def choose_method() -> str:
    review = pd.read_csv(DATA_DIR / "review_summary.csv")
    scores = {}
    for method in METHOD_FILES:
        scores[method] = review[f"{method}_detected"].sum() - review[f"{method}_false"].sum()
    return max(scores, key=scores.get)


def remove_blasts(frame: pd.DataFrame) -> pd.DataFrame:
    blasts = pd.read_csv(DATA_DIR / "blast_windows.csv")
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"])
    blasts["start_time"] = pd.to_datetime(blasts["start_time"])
    blasts["end_time"] = pd.to_datetime(blasts["end_time"])
    keep_mask = pd.Series(True, index=frame.index)
    for blast in blasts.itertuples(index=False):
        keep_mask &= ~frame["time"].between(blast.start_time, blast.end_time, inclusive="both")
    return frame.loc[keep_mask].copy()


def collapse_duplicates(frame: pd.DataFrame) -> pd.DataFrame:
    kept_groups = []
    for _, family_frame in frame.groupby("repeater_family", sort=False):
        family_frame = family_frame.sort_values("time")
        chosen_rows = []
        for row in family_frame.itertuples(index=False):
            if not chosen_rows:
                chosen_rows.append(row)
                continue
            previous = chosen_rows[-1]
            gap = (row.time - previous.time).total_seconds()
            if gap <= 1.5:
                if row.correlation_peak > previous.correlation_peak:
                    chosen_rows[-1] = row
                elif row.correlation_peak == previous.correlation_peak:
                    if row.sensor_count > previous.sensor_count:
                        chosen_rows[-1] = row
                    elif row.sensor_count == previous.sensor_count and row.time < previous.time:
                        chosen_rows[-1] = row
            else:
                chosen_rows.append(row)
        kept_groups.append(pd.DataFrame(chosen_rows))

    result = pd.concat(kept_groups, ignore_index=True)
    result = result.sort_values("time").reset_index(drop=True)
    result["time"] = result["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return result


method = choose_method()
catalog = pd.read_csv(DATA_DIR / METHOD_FILES[method])
catalog = remove_blasts(catalog)
catalog = collapse_duplicates(catalog)
catalog["method_family"] = method
catalog = catalog[
    [
        "time",
        "repeater_family",
        "template_id",
        "sensor_count",
        "correlation_peak",
        "method_family",
    ]
]
catalog.to_csv(OUTPUT_FILE, index=False)
PY
