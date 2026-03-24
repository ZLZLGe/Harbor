import json
import os
from typing import Any

import pandas as pd

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", os.environ.get("OUTPUT_DIR", "/app/output"))

OUT_FILE = os.path.join(OUT_DIR, "defect_containment_card.json")

PREHEAT_MIN_C = 100.0
PREHEAT_MAX_C = 150.0
RAMP_LIMIT_C_S = 2.0
TAL_MIN_S = 30.0
TAL_MAX_S = 60.0
PEAK_MARGIN_C = 20.0
REFERENCE_TC_ROLE = "largest_mass"
THERMAL_DEFECTS = {
    "insufficient_solder",
    "head_in_pillow",
    "voiding",
    "dull_joints",
    "bridging",
    "solder_balls",
    "tombstone",
}
WETTING_DEFECTS = {"insufficient_solder", "head_in_pillow", "voiding", "dull_joints"}
RAMP_DEFECTS = {"bridging", "solder_balls", "tombstone"}
OXYGEN_LIMITS = {"N2_full": 500.0, "N2_mixed": 1000.0, "Air": None}


def round2(value: float) -> float:
    return float(round(float(value), 2))


def load_json(path: str) -> Any:
    assert os.path.exists(path), f"missing output: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_inputs() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    with open(os.path.join(DATA_DIR, "incident_context.json"), "r", encoding="utf-8") as f:
        context = json.load(f)
    runs = pd.read_csv(os.path.join(DATA_DIR, "incident_runs.csv"))
    defects = pd.read_csv(os.path.join(DATA_DIR, "defect_distribution.csv"))
    traces = pd.read_csv(os.path.join(DATA_DIR, "incident_traces.csv"))
    mes = pd.read_csv(os.path.join(DATA_DIR, "mes_unit_history.csv"))
    for frame in [runs, defects, traces, mes]:
        for column in frame.columns:
            if frame[column].dtype == object:
                frame[column] = frame[column].astype(str)
    return context, runs, defects, traces, mes


def max_preheat_ramp(trace: pd.DataFrame) -> float:
    trace = trace.sort_values("time_s", kind="mergesort")
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
    trace = trace.sort_values("time_s", kind="mergesort")
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


def expected_analysis() -> list[dict[str, Any]]:
    _, runs, defects, traces, _ = load_inputs()
    runs_by_id = runs.set_index("run_id")

    thermal_counts = (
        defects[
            defects["inspection_stage"].isin(["AOI", "VISUAL"])
            & defects["defect_type"].isin(sorted(THERMAL_DEFECTS))
        ]
        .groupby("run_id", sort=True)["defect_count"]
        .sum()
        .to_dict()
    )

    escape_ids = []
    for _, row in runs.sort_values("run_id", kind="mergesort").iterrows():
        if str(row["defect_trend"]) == "up" and int(thermal_counts.get(str(row["run_id"]), 0)) >= 20:
            escape_ids.append(str(row["run_id"]))

    rows = []
    for run_id in escape_ids:
        trace = traces[(traces["run_id"] == run_id) & (traces["tc_role"] == REFERENCE_TC_ROLE)].copy()
        liquidus = float(runs_by_id.loc[run_id, "solder_liquidus_c"])
        required_min_peak = round2(liquidus + PEAK_MARGIN_C)
        defect_totals = (
            defects[defects["run_id"] == run_id]
            .groupby("defect_type", sort=True)["defect_count"]
            .sum()
            .reset_index()
            .sort_values(["defect_count", "defect_type"], ascending=[False, True], kind="mergesort")
        )
        dominant_defect = str(defect_totals.iloc[0]["defect_type"])
        oxygen_limit = OXYGEN_LIMITS[str(runs_by_id.loc[run_id, "gas_mode"])]
        oxygen_over = oxygen_limit is not None and float(runs_by_id.loc[run_id, "o2_ppm_reflow"]) > float(oxygen_limit)
        rows.append(
            {
                "run_id": run_id,
                "lot_id": str(runs_by_id.loc[run_id, "lot_id"]),
                "dominant_defect": dominant_defect,
                "escape_defect_total": int(thermal_counts[run_id]),
                "ramp_c_per_s": max_preheat_ramp(trace),
                "tal_s": tal_seconds(trace, liquidus),
                "peak_temp_c": peak_temp(trace),
                "required_min_peak_c": required_min_peak,
                "signal_flags": {
                    "ramp_violation": max_preheat_ramp(trace) > RAMP_LIMIT_C_S,
                    "tal_low": tal_seconds(trace, liquidus) < TAL_MIN_S,
                    "peak_low": peak_temp(trace) < required_min_peak,
                    "oxygen_over_limit": oxygen_over,
                },
            }
        )
    return sorted(rows, key=lambda row: row["run_id"])


def expected_mode(actual_analysis: list[dict[str, Any]]) -> tuple[str, list[str], dict[str, list[str]]]:
    center_runs = sorted(
        row["run_id"]
        for row in actual_analysis
        if row["signal_flags"]["tal_low"]
        and row["signal_flags"]["peak_low"]
        and row["dominant_defect"] in WETTING_DEFECTS
    )
    nitrogen_runs = sorted(
        row["run_id"]
        for row in actual_analysis
        if row["signal_flags"]["oxygen_over_limit"] and row["dominant_defect"] in WETTING_DEFECTS
    )
    ramp_runs = sorted(
        row["run_id"]
        for row in actual_analysis
        if row["signal_flags"]["ramp_violation"] and row["dominant_defect"] in RAMP_DEFECTS
    )
    evidence = {
        "dominant_defects": sorted({row["dominant_defect"] for row in actual_analysis}),
        "tal_below_runs": sorted(row["run_id"] for row in actual_analysis if row["signal_flags"]["tal_low"]),
        "peak_below_runs": sorted(row["run_id"] for row in actual_analysis if row["signal_flags"]["peak_low"]),
        "ramp_violation_runs": ramp_runs,
        "oxygen_over_limit_runs": sorted(
            row["run_id"] for row in actual_analysis if row["signal_flags"]["oxygen_over_limit"]
        ),
    }
    if len(center_runs) >= 2:
        return "center_zone_heat_loss", center_runs, evidence
    if len(nitrogen_runs) >= 2:
        return "nitrogen_path_leak", nitrogen_runs, evidence
    if len(ramp_runs) >= 1:
        return "entry_ramp_overshoot", ramp_runs, evidence
    return "recipe_loading_shift", sorted(row["run_id"] for row in actual_analysis), evidence


def test_window_reference_and_analysis_rows() -> None:
    actual = load_json(OUT_FILE)
    expected = expected_analysis()
    assert actual["window_reference"] == {
        "reference_tc_role": REFERENCE_TC_ROLE,
        "preheat_band_c": [round2(PREHEAT_MIN_C), round2(PREHEAT_MAX_C)],
        "max_ramp_c_per_s": round2(RAMP_LIMIT_C_S),
        "tal_window_s": [round2(TAL_MIN_S), round2(TAL_MAX_S)],
        "peak_margin_above_liquidus_c": round2(PEAK_MARGIN_C),
    }
    assert actual["escape_run_analysis"] == expected


def test_failure_mode_priority_and_evidence() -> None:
    actual = load_json(OUT_FILE)
    analysis = expected_analysis()
    mode_code, trigger_runs, evidence = expected_mode(analysis)
    subsystem_map = {
        "center_zone_heat_loss": "center_heating_zones",
        "nitrogen_path_leak": "nitrogen_delivery_path",
        "entry_ramp_overshoot": "entry_ramp_section",
        "recipe_loading_shift": "loaded_profile_review",
    }
    confidence = "high" if len(trigger_runs) >= 2 else "medium" if len(trigger_runs) == 1 else "low"
    assert actual["suspected_failure_mode"]["mode_code"] == mode_code
    assert actual["suspected_failure_mode"]["priority_subsystem"] == subsystem_map[mode_code]
    assert actual["suspected_failure_mode"]["confidence"] == confidence
    assert actual["suspected_failure_mode"]["trigger_run_ids"] == trigger_runs
    assert actual["suspected_failure_mode"]["evidence"] == evidence


def test_containment_scope_matches_mes_rows() -> None:
    actual = load_json(OUT_FILE)
    _, runs, _, _, mes = load_inputs()
    trigger_runs = actual["suspected_failure_mode"]["trigger_run_ids"]
    rows = mes[mes["run_id"].isin(trigger_runs)].copy().sort_values("panel_sn", kind="mergesort")
    hold_rows = rows[rows["disposition"] != "shipped"].copy()
    expected_scope = {
        "affected_run_ids": sorted(trigger_runs),
        "affected_lot_ids": sorted(runs[runs["run_id"].isin(trigger_runs)]["lot_id"].astype(str).unique().tolist()),
        "serial_span": [str(rows["panel_sn"].min()), str(rows["panel_sn"].max())],
        "panels_to_hold": int(len(hold_rows)),
        "shipped_panels": int((rows["disposition"] == "shipped").sum()),
        "hold_locations": sorted(hold_rows["current_location"].astype(str).unique().tolist()),
    }
    assert actual["containment_scope"] == expected_scope


def test_action_card_is_center_zone_template() -> None:
    actual = load_json(OUT_FILE)
    assert actual["incident_id"] == "QE-ESC-2026-0318"
    assert actual["line_id"] == "RF-07"
    actions = actual["immediate_actions"]
    assert [row["step"] for row in actions] == [1, 2, 3]
    assert [row["owner_role"] for row in actions] == [
        "quality_engineer",
        "line_lead",
        "maintenance_technician",
    ]
    assert actual["suspected_failure_mode"]["mode_code"] == "center_zone_heat_loss"
    assert "zones 5-7 heater output" in actions[2]["action"]
    assert "wetting-related" in actions[1]["reason"]

    card = actual["technician_action_card"]
    assert card["subsystem"] == "center_heating_zones"
    assert card["inspection_points"] == sorted(
        [
            "Check zone 5-7 heater feedback versus setpoint.",
            "Confirm center-zone blower circulation is stable across both rails.",
            "Inspect conveyor loading balance and shadowing at the board center mass.",
        ]
    )
    assert card["parameter_checks"] == sorted(
        [
            "O2 is not the primary trigger for this incident; do not release only on nitrogen data.",
            "Peak temperature must be at least liquidus + 20.00 C.",
            "TAL must recover to 30.00-60.00 s on the representative thermocouple.",
        ]
    )
    assert "TAL and peak both recovered" in card["release_condition"]
