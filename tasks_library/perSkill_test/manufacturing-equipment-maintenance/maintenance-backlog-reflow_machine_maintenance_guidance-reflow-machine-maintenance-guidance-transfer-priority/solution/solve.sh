#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import json
import os

import pandas as pd

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")

OUT_FILE = os.path.join(OUT_DIR, "maintenance_priority_board.json")

PREHEAT_MIN_C = 100.0
PREHEAT_MAX_C = 150.0
RAMP_LIMIT_C_S = 2.0
TAL_MIN_S = 30.0
TAL_MAX_S = 60.0
PEAK_MARGIN_C = 20.0
REFERENCE_TC_ROLE = "largest_mass"

OXYGEN_CAPS = {
    "Air": None,
    "N2_full": 500.0,
    "N2_mixed": 1000.0,
}
WETTING_DEFECTS = {"insufficient_solder", "voiding", "head_in_pillow"}
RAMP_DEFECTS = {"bridging", "solder_balls", "tombstone"}


def round2(value: float) -> float:
    return float(round(float(value), 2))


def max_preheat_ramp(trace: pd.DataFrame) -> float:
    trace = trace.sort_values("time_s")
    best = None
    for i in range(1, len(trace)):
        prev = trace.iloc[i - 1]
        curr = trace.iloc[i]
        dt = float(curr["time_s"]) - float(prev["time_s"])
        if dt <= 0:
            continue
        y0 = float(prev["temp_c"])
        y1 = float(curr["temp_c"])
        if PREHEAT_MIN_C <= y0 <= PREHEAT_MAX_C and PREHEAT_MIN_C <= y1 <= PREHEAT_MAX_C:
            slope = (y1 - y0) / dt
            best = slope if best is None else max(best, slope)
    return round2(best if best is not None else 0.0)


def tal_seconds(trace: pd.DataFrame, threshold: float) -> float:
    trace = trace.sort_values("time_s")
    total = 0.0
    for i in range(1, len(trace)):
        prev = trace.iloc[i - 1]
        curr = trace.iloc[i]
        t0 = float(prev["time_s"])
        t1 = float(curr["time_s"])
        y0 = float(prev["temp_c"])
        y1 = float(curr["temp_c"])
        if t1 <= t0:
            continue
        if y0 > threshold and y1 > threshold:
            total += t1 - t0
            continue
        crosses = (y0 <= threshold < y1) or (y1 <= threshold < y0)
        if crosses and y1 != y0:
            frac = (threshold - y0) / (y1 - y0)
            cross_t = t0 + frac * (t1 - t0)
            total += (t1 - cross_t) if y0 <= threshold < y1 else (cross_t - t0)
    return round2(total)


def peak_temp(trace: pd.DataFrame) -> float:
    return round2(trace["temp_c"].astype(float).max())


def first_check_reason(machine_id: str, subsystem: str, score_breakdown: dict[str, float], evidence: dict[str, object]) -> str:
    if subsystem == "nitrogen_delivery_path":
        return (
            f"{machine_id} has repeated oxygen-cap breaches aligned with wetting defects and low-energy profiles, "
            "so the nitrogen delivery path should be checked first."
        )
    if subsystem == "center_heating_zones":
        return (
            f"{machine_id} shows repeated TAL-low and peak-low representative traces, "
            "which points to insufficient center-zone heat delivery."
        )
    if subsystem == "entry_ramp_section":
        return (
            f"{machine_id} exceeds the preheat ramp limit on representative traces while ramp-related defects are rising, "
            "so the entry ramp section is the first check."
        )
    if subsystem == "thermocouple_chain":
        return (
            f"{machine_id} does not have a stronger process-window trigger, but repeated thermocouple drift events and overdue PM make the thermocouple chain the first check."
        )
    return (
        f"{machine_id} has no rule-based urgent trigger, so keep it at the bottom of the backlog and inspect it in the next planned PM window."
    )


machines = pd.read_csv(os.path.join(DATA_DIR, "machine_backlog.csv"))
downtime = pd.read_csv(os.path.join(DATA_DIR, "downtime_breakdown.csv"))
runs = pd.read_csv(os.path.join(DATA_DIR, "recent_runs.csv"))
traces = pd.read_csv(os.path.join(DATA_DIR, "weekly_traces.csv"))

machines["machine_id"] = machines["machine_id"].astype(str)
downtime["machine_id"] = downtime["machine_id"].astype(str)
downtime["subsystem_code"] = downtime["subsystem_code"].astype(str)
runs["run_id"] = runs["run_id"].astype(str)
runs["machine_id"] = runs["machine_id"].astype(str)
runs["gas_mode"] = runs["gas_mode"].astype(str)
runs["dominant_defect"] = runs["dominant_defect"].astype(str)
runs["defect_trend"] = runs["defect_trend"].astype(str)
traces["run_id"] = traces["run_id"].astype(str)
traces["tc_role"] = traces["tc_role"].astype(str)

run_metrics = []
for _, row in runs.sort_values(["machine_id", "run_id"], kind="mergesort").iterrows():
    run_id = str(row["run_id"])
    trace = traces[(traces["run_id"] == run_id) & (traces["tc_role"] == REFERENCE_TC_ROLE)].copy()
    liquidus = float(row["solder_liquidus_c"])
    run_metrics.append(
        {
            "run_id": run_id,
            "machine_id": str(row["machine_id"]),
            "gas_mode": str(row["gas_mode"]),
            "o2_ppm_reflow": float(row["o2_ppm_reflow"]),
            "dominant_defect": str(row["dominant_defect"]),
            "defect_trend": str(row["defect_trend"]),
            "ramp_c_per_s": max_preheat_ramp(trace),
            "tal_s": tal_seconds(trace, liquidus),
            "peak_temp_c": peak_temp(trace),
            "required_min_peak_c": round2(liquidus + PEAK_MARGIN_C),
        }
    )

run_df = pd.DataFrame(run_metrics)

machine_rows = []
for _, machine in machines.sort_values("machine_id", kind="mergesort").iterrows():
    machine_id = str(machine["machine_id"])
    group = run_df[run_df["machine_id"] == machine_id].copy()

    oxygen_runs = []
    tal_low_runs = []
    peak_low_runs = []
    ramp_violation_runs = []
    for _, run in group.sort_values("run_id", kind="mergesort").iterrows():
        cap = OXYGEN_CAPS[str(run["gas_mode"])]
        if (
            cap is not None
            and float(run["o2_ppm_reflow"]) > cap
            and str(run["dominant_defect"]) in WETTING_DEFECTS
            and str(run["defect_trend"]) == "up"
        ):
            oxygen_runs.append(str(run["run_id"]))
        if float(run["tal_s"]) < TAL_MIN_S:
            tal_low_runs.append(str(run["run_id"]))
        if float(run["peak_temp_c"]) < float(run["required_min_peak_c"]):
            peak_low_runs.append(str(run["run_id"]))
        if (
            float(run["ramp_c_per_s"]) > RAMP_LIMIT_C_S
            and str(run["dominant_defect"]) in RAMP_DEFECTS
            and str(run["defect_trend"]) == "up"
        ):
            ramp_violation_runs.append(str(run["run_id"]))

    heat_delivery_runs = sorted(set(tal_low_runs) & set(peak_low_runs))

    score_breakdown = {
        "oxygen_wetting_risk": round2(40.0 if len(oxygen_runs) >= 2 else 0.0),
        "heat_delivery_risk": round2(35.0 if len(heat_delivery_runs) >= 2 else 0.0),
        "ramp_risk": round2(25.0 if ramp_violation_runs else 0.0),
        "sensor_instability": round2(20.0 if int(machine["tc_drift_events_7d"]) >= 2 else 0.0),
        "maintenance_overdue": round2(15.0 if int(machine["maintenance_overdue"]) == 1 else 0.0),
        "downtime_burden": round2(10.0 if int(machine["downtime_minutes_7d"]) >= 120 else 0.0),
    }
    priority_score = round2(sum(score_breakdown.values()))

    if score_breakdown["oxygen_wetting_risk"] > 0:
        subsystem = "nitrogen_delivery_path"
    elif score_breakdown["heat_delivery_risk"] > 0:
        subsystem = "center_heating_zones"
    elif score_breakdown["ramp_risk"] > 0:
        subsystem = "entry_ramp_section"
    elif score_breakdown["sensor_instability"] > 0:
        subsystem = "thermocouple_chain"
    else:
        subsystem = "planned_pm_window"

    if priority_score >= 80.0:
        band = "urgent"
    elif priority_score >= 50.0:
        band = "high"
    elif priority_score >= 25.0:
        band = "medium"
    else:
        band = "low"

    stop_rows = downtime[downtime["machine_id"] == machine_id].copy()
    stop_rows = stop_rows.sort_values(["downtime_minutes_7d", "subsystem_code"], ascending=[False, True], kind="mergesort")
    largest_stop_subsystem = str(stop_rows.iloc[0]["subsystem_code"])

    dominant_defects = sorted(group["dominant_defect"].astype(str).unique().tolist())
    evidence = {
        "largest_stop_subsystem": largest_stop_subsystem,
        "downtime_minutes_7d": int(machine["downtime_minutes_7d"]),
        "tc_drift_events_7d": int(machine["tc_drift_events_7d"]),
        "over_limit_oxygen_runs": sorted(oxygen_runs),
        "tal_low_runs": sorted(tal_low_runs),
        "peak_low_runs": sorted(peak_low_runs),
        "ramp_violation_runs": sorted(ramp_violation_runs),
        "dominant_defects": dominant_defects,
    }

    machine_rows.append(
        {
            "machine_id": machine_id,
            "priority_band": band,
            "priority_score": priority_score,
            "first_check_subsystem": subsystem,
            "score_breakdown": score_breakdown,
            "evidence": evidence,
            "why_this_first": first_check_reason(machine_id, subsystem, score_breakdown, evidence),
        }
    )

machine_rows.sort(key=lambda item: (-item["priority_score"], item["machine_id"]))
for index, row in enumerate(machine_rows, start=1):
    row["priority_rank"] = index

output = {
    "board_name": "weekly_reflow_maintenance_backlog",
    "window_reference": {
        "reference_tc_role": REFERENCE_TC_ROLE,
        "preheat_band_c": [round2(PREHEAT_MIN_C), round2(PREHEAT_MAX_C)],
        "max_ramp_c_per_s": round2(RAMP_LIMIT_C_S),
        "tal_window_s": [round2(TAL_MIN_S), round2(TAL_MAX_S)],
        "peak_margin_above_liquidus_c": round2(PEAK_MARGIN_C),
    },
    "machines": machine_rows,
}

os.makedirs(OUT_DIR, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
PY
