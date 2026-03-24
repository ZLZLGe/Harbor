#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

APP_ROOT = os.environ.get("APP_ROOT", "/app")
DATA_DIR = os.path.join(APP_ROOT, "data")
OUT_DIR = os.path.join(APP_ROOT, "output")
OUT_PATH = os.path.join(OUT_DIR, "first_article_release.json")
os.makedirs(OUT_DIR, exist_ok=True)

RUNS_CSV = os.path.join(DATA_DIR, "first_article_runs.csv")
TC_CSV = os.path.join(DATA_DIR, "first_article_thermocouples.csv")
DEFECTS_CSV = os.path.join(DATA_DIR, "first_article_defects.csv")

PREHEAT_MIN_C = 100.0
PREHEAT_MAX_C = 150.0
RAMP_LIMIT_C_PER_S = 2.0
TAL_MIN_S = 30.0
TAL_MAX_S = 60.0
PEAK_MARGIN_C = 20.0

FAILURE_REASON_ORDER = [
    "preheat_ramp_exceeds_limit",
    "tal_out_of_window",
    "peak_margin_not_met",
    "critical_defects_present",
    "yield_below_95",
]


def round2(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(round(float(value), 2))


def max_preheat_ramp(group: pd.DataFrame) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    best = None
    times = group["time_s"].astype(float).tolist()
    temps = group["temp_c"].astype(float).tolist()
    for idx in range(1, len(group)):
        t0 = times[idx - 1]
        t1 = times[idx]
        y0 = temps[idx - 1]
        y1 = temps[idx]
        if t1 <= t0:
            continue
        if PREHEAT_MIN_C <= y0 <= PREHEAT_MAX_C and PREHEAT_MIN_C <= y1 <= PREHEAT_MAX_C:
            slope = (y1 - y0) / (t1 - t0)
            best = slope if best is None else max(best, slope)
    return None if best is None else round2(best)


def tal_seconds(group: pd.DataFrame, threshold: float) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    total = 0.0
    times = group["time_s"].astype(float).tolist()
    temps = group["temp_c"].astype(float).tolist()
    for idx in range(1, len(group)):
        t0 = times[idx - 1]
        t1 = times[idx]
        y0 = temps[idx - 1]
        y1 = temps[idx]
        if t1 <= t0:
            continue
        if y0 > threshold and y1 > threshold:
            total += (t1 - t0)
            continue
        crosses = (y0 <= threshold < y1) or (y1 <= threshold < y0)
        if crosses and y1 != y0:
            fraction = (threshold - y0) / (y1 - y0)
            t_cross = t0 + fraction * (t1 - t0)
            if y0 <= threshold and y1 > threshold:
                total += (t1 - t_cross)
            else:
                total += (t_cross - t0)
    return round2(total)


def representative_tc(run_tc: pd.DataFrame) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    candidates: List[Tuple[float, str, pd.DataFrame]] = []
    for tc_id, group in run_tc.groupby("tc_id", sort=False):
        peak = float(group["temp_c"].max())
        candidates.append((peak, str(tc_id), group))
    if not candidates:
        return (None, None, None)
    peak, tc_id, group = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
    return (tc_id, round2(peak), tal_seconds(group, 217.0))


def fail_codes(
    ramp: Optional[float],
    tal: Optional[float],
    peak: Optional[float],
    required_min_peak: float,
    critical_count: int,
    yield_pct: float,
) -> List[str]:
    codes: List[str] = []
    if ramp is None or ramp > RAMP_LIMIT_C_PER_S:
        codes.append("preheat_ramp_exceeds_limit")
    if tal is None or tal < TAL_MIN_S or tal > TAL_MAX_S:
        codes.append("tal_out_of_window")
    if peak is None or peak < required_min_peak:
        codes.append("peak_margin_not_met")
    if critical_count > 0:
        codes.append("critical_defects_present")
    if yield_pct < 95.0:
        codes.append("yield_below_95")
    order = {code: idx for idx, code in enumerate(FAILURE_REASON_ORDER)}
    return sorted(codes, key=lambda code: order[code])


runs = pd.read_csv(RUNS_CSV)
thermocouples = pd.read_csv(TC_CSV)
defects = pd.read_csv(DEFECTS_CSV)

runs["run_id"] = runs["run_id"].astype(str)
runs["board_id"] = runs["board_id"].astype(str)
thermocouples["run_id"] = thermocouples["run_id"].astype(str)
thermocouples["tc_id"] = thermocouples["tc_id"].astype(str)
defects["run_id"] = defects["run_id"].astype(str)
defects["inspection_stage"] = defects["inspection_stage"].astype(str)
defects["severity"] = defects["severity"].fillna("").astype(str)

runs = runs.sort_values(["run_id"], kind="mergesort")
thermocouples = thermocouples.sort_values(["run_id", "tc_id", "time_s"], kind="mergesort")
defects = defects.sort_values(["run_id", "inspection_stage", "defect_type"], kind="mergesort")

board_id = sorted(runs["board_id"].unique().tolist())[0]
run_records: List[Dict[str, Any]] = []

for run_id, run_row in runs.set_index("run_id").sort_index().iterrows():
    run_tc = thermocouples[thermocouples["run_id"] == run_id]
    rep_tc_id, peak_temp_c, tal_s = representative_tc(run_tc)
    ramp_values = [
        value
        for _, tc_group in run_tc.groupby("tc_id", sort=False)
        for value in [max_preheat_ramp(tc_group)]
        if value is not None
    ]
    max_ramp = round2(max(ramp_values)) if ramp_values else None

    defect_rows = defects[defects["run_id"] == run_id]
    summary_rows = defect_rows[defect_rows["inspection_stage"] == "SUMMARY"]
    summary = summary_rows.iloc[0]
    critical_count = int(
        defect_rows[(defect_rows["inspection_stage"] != "SUMMARY") & (defect_rows["severity"] == "critical")]["count"].sum()
    )
    total_defects = int(defect_rows[defect_rows["inspection_stage"] != "SUMMARY"]["count"].sum())
    yield_pct = round2(float(summary["fp_yield_pct"]))
    required_min_peak_c = round2(float(run_row["solder_liquidus_c"]) + PEAK_MARGIN_C)

    thermal_pass = (
        max_ramp is not None
        and max_ramp <= RAMP_LIMIT_C_PER_S
        and tal_s is not None
        and TAL_MIN_S <= tal_s <= TAL_MAX_S
        and peak_temp_c is not None
        and peak_temp_c >= required_min_peak_c
    )
    quality_pass = critical_count == 0 and yield_pct is not None and yield_pct >= 95.0
    reasons = fail_codes(max_ramp, tal_s, peak_temp_c, required_min_peak_c, critical_count, float(yield_pct))

    run_records.append(
        {
            "run_id": run_id,
            "representative_tc_id": rep_tc_id,
            "max_preheat_ramp_c_per_s": max_ramp,
            "tal_s": tal_s,
            "peak_temp_c": peak_temp_c,
            "required_min_peak_c": required_min_peak_c,
            "fp_yield_pct": yield_pct,
            "critical_defect_count": critical_count,
            "total_defect_count": total_defects,
            "thermal_status": "pass" if thermal_pass else "fail",
            "quality_status": "pass" if quality_pass else "fail",
            "release_decision": "release" if thermal_pass and quality_pass else "hold",
            "failure_reasons": reasons,
        }
    )

run_records.sort(key=lambda row: row["run_id"])
released = sorted([row["run_id"] for row in run_records if row["release_decision"] == "release"])
blocked = sorted([row["run_id"] for row in run_records if row["release_decision"] == "hold"])

golden_run_id = None
if released:
    ranked = sorted(
        [row for row in run_records if row["release_decision"] == "release"],
        key=lambda row: (
            -float(row["fp_yield_pct"]),
            int(row["total_defect_count"]),
            float(row["max_preheat_ramp_c_per_s"]),
            row["run_id"],
        ),
    )
    golden_run_id = ranked[0]["run_id"]

result = {
    "board_id": board_id,
    "handbook_limits": {
        "preheat_temp_min_c": round2(PREHEAT_MIN_C),
        "preheat_temp_max_c": round2(PREHEAT_MAX_C),
        "ramp_limit_c_per_s": round2(RAMP_LIMIT_C_PER_S),
        "tal_min_s": round2(TAL_MIN_S),
        "tal_max_s": round2(TAL_MAX_S),
        "peak_margin_c": round2(PEAK_MARGIN_C),
        "representative_tc_rule": "lowest_peak_then_smallest_tc_id",
    },
    "released_run_ids": released,
    "blocked_run_ids": blocked,
    "golden_run_id": golden_run_id,
    "runs": run_records,
}

with open(OUT_PATH, "w", encoding="utf-8") as output_file:
    json.dump(result, output_file, indent=2, ensure_ascii=False)
PY
