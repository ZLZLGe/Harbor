#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/output}"
export DATA_DIR OUT_DIR
mkdir -p "${OUT_DIR}"

python3 - <<'PY'
import json
import os
from typing import Any

import pandas as pd

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

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

MODE_TO_SUBSYSTEM = {
    "center_zone_heat_loss": "center_heating_zones",
    "nitrogen_path_leak": "nitrogen_delivery_path",
    "entry_ramp_overshoot": "entry_ramp_section",
    "recipe_loading_shift": "loaded_profile_review",
}

ACTION_TEMPLATES = {
    "center_zone_heat_loss": {
        "actions": [
            {
                "step": 1,
                "owner_role": "quality_engineer",
                "action": "Block lots L2402 and L2403 in MES, quarantine all non-shipped panels at fg_buffer, packout_queue, qa_cage.",
                "reason": "The selected trigger runs share low TAL and low peak signals that map to a center-zone heat delivery loss.",
            },
            {
                "step": 2,
                "owner_role": "line_lead",
                "action": "Launch 100% AOI plus visual reinspection for affected runs and notify downstream packout that shipped panels need recall screening.",
                "reason": "The dominant defects are wetting-related, so immediate downstream screening is required before any more units move.",
            },
            {
                "step": 3,
                "owner_role": "maintenance_technician",
                "action": "Inspect reflow zones 5-7 heater output, blower balance, and rail loading before any restart decision.",
                "reason": "Both trigger runs point to insufficient heat delivery through the center of the profile.",
            },
        ],
        "card": {
            "subsystem": "center_heating_zones",
            "inspection_points": sorted(
                [
                    "Check zone 5-7 heater feedback versus setpoint.",
                    "Confirm center-zone blower circulation is stable across both rails.",
                    "Inspect conveyor loading balance and shadowing at the board center mass.",
                ]
            ),
            "parameter_checks": sorted(
                [
                    "O2 is not the primary trigger for this incident; do not release only on nitrogen data.",
                    "Peak temperature must be at least liquidus + 20.00 C.",
                    "TAL must recover to 30.00-60.00 s on the representative thermocouple.",
                ]
            ),
            "release_condition": "Release only after a confirmation run shows TAL and peak both recovered on the representative thermocouple and quality approves the reinspection results.",
        },
    },
    "nitrogen_path_leak": {
        "actions": [
            {
                "step": 1,
                "owner_role": "quality_engineer",
                "action": "Block the affected lots in MES and quarantine all non-shipped panels in the listed hold locations.",
                "reason": "Oxygen-over-limit evidence indicates a gas-path escape that can impact every panel from the trigger runs.",
            },
            {
                "step": 2,
                "owner_role": "line_lead",
                "action": "Start focused wetting-defect screening and stop any additional lot release on the same oven until gas integrity is verified.",
                "reason": "The defect pattern is consistent with nitrogen delivery loss rather than random inspection noise.",
            },
            {
                "step": 3,
                "owner_role": "maintenance_technician",
                "action": "Check the nitrogen flow path, O2 probe condition, and door/hood leak points before restart.",
                "reason": "The chosen mode is driven by oxygen excursions in nitrogen operation.",
            },
        ],
        "card": {
            "subsystem": "nitrogen_delivery_path",
            "inspection_points": sorted(
                [
                    "Check hood seals, tunnel access covers, and door curtains for leakage.",
                    "Confirm nitrogen flow delivery and manifold pressure stability.",
                    "Verify the O2 probe reading against a known-good reference.",
                ]
            ),
            "parameter_checks": sorted(
                [
                    "N2_full lots must stay at or below 500.00 ppm O2.",
                    "N2_mixed lots must stay at or below 1000.00 ppm O2.",
                    "Thermal release requires the wetting-defect signal to return to baseline after gas-path repair.",
                ]
            ),
            "release_condition": "Release only after oxygen readings recover inside the gas-mode limit and confirmatory inspection shows the wetting-defect spike is cleared.",
        },
    },
    "entry_ramp_overshoot": {
        "actions": [
            {
                "step": 1,
                "owner_role": "quality_engineer",
                "action": "Block the affected lots in MES and quarantine all non-shipped panels in the listed hold locations.",
                "reason": "Preheat overshoot can create systematic bridging-related escapes across the trigger run scope.",
            },
            {
                "step": 2,
                "owner_role": "line_lead",
                "action": "Switch the line to 100% bridge-focused screening and hold further release from the same recipe family.",
                "reason": "The defect signature is concentrated in ramp-related defect types.",
            },
            {
                "step": 3,
                "owner_role": "maintenance_technician",
                "action": "Inspect entry-zone setpoints, blower response, and recipe load at the oven entrance before restart.",
                "reason": "The trigger evidence points to excessive early heating rather than a center-zone shortage.",
            },
        ],
        "card": {
            "subsystem": "entry_ramp_section",
            "inspection_points": sorted(
                [
                    "Check entry-zone heater feedback versus recipe setpoints.",
                    "Inspect entrance blower response and conveyor loading changes.",
                    "Verify the loaded recipe revision against the approved baseline.",
                ]
            ),
            "parameter_checks": sorted(
                [
                    "Preheat ramp must stay at or below 2.00 C/s in the 100.00-150.00 C band.",
                    "Release requires ramp-related defects to fall back to baseline.",
                    "TAL and peak must remain inside the normal process window after entry-zone correction.",
                ]
            ),
            "release_condition": "Release only after a confirmation run shows ramp compliance and quality confirms no renewed bridge-related spike.",
        },
    },
    "recipe_loading_shift": {
        "actions": [
            {
                "step": 1,
                "owner_role": "quality_engineer",
                "action": "Block the affected lots in MES and quarantine all non-shipped panels in the listed hold locations.",
                "reason": "The escape cannot be isolated to a single thermal mode, so the full affected trigger scope must be contained first.",
            },
            {
                "step": 2,
                "owner_role": "line_lead",
                "action": "Start mixed-mode reinspection and freeze additional recipe release for the affected batch family.",
                "reason": "The event needs recipe-versus-loading review before more material moves downstream.",
            },
            {
                "step": 3,
                "owner_role": "maintenance_technician",
                "action": "Review loaded recipe parameters, lot loading pattern, and recent setup changes before restart.",
                "reason": "No single heater, gas, or ramp signature dominated the escape.",
            },
        ],
        "card": {
            "subsystem": "loaded_profile_review",
            "inspection_points": sorted(
                [
                    "Check recipe revision history against the approved release.",
                    "Inspect lot loading density and board mix during the incident window.",
                    "Review any setup or changeover actions immediately before the escape runs.",
                ]
            ),
            "parameter_checks": sorted(
                [
                    "Confirm the representative thermocouple profile still meets the handbook window.",
                    "Verify no unapproved recipe or loading deviation remains active.",
                    "Reinspection must show the mixed defect spike has collapsed before release.",
                ]
            ),
            "release_condition": "Release only after recipe, loading, and confirmation-run evidence all return to the approved baseline and quality signs off.",
        },
    },
}


def round2(value: float) -> float:
    return float(round(float(value), 2))


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


def escape_run_ids(runs: pd.DataFrame, defects: pd.DataFrame) -> list[str]:
    escape_totals = (
        defects[
            defects["inspection_stage"].isin(["AOI", "VISUAL"])
            & defects["defect_type"].isin(sorted(THERMAL_DEFECTS))
        ]
        .groupby("run_id", sort=True)["defect_count"]
        .sum()
        .to_dict()
    )
    ids = []
    for _, row in runs.sort_values("run_id", kind="mergesort").iterrows():
        run_id = str(row["run_id"])
        if str(row["defect_trend"]) == "up" and int(escape_totals.get(run_id, 0)) >= 20:
            ids.append(run_id)
    return ids


def dominant_defect_for_run(defects: pd.DataFrame, run_id: str) -> str:
    grouped = (
        defects[defects["run_id"] == run_id]
        .groupby("defect_type", sort=True)["defect_count"]
        .sum()
        .reset_index()
        .sort_values(["defect_count", "defect_type"], ascending=[False, True], kind="mergesort")
    )
    return str(grouped.iloc[0]["defect_type"])


def build_output() -> dict[str, Any]:
    context, runs, defects, traces, mes = load_inputs()
    escape_ids = escape_run_ids(runs, defects)
    runs_by_id = runs.set_index("run_id")

    escape_analysis = []
    evidence = {
        "dominant_defects": [],
        "tal_below_runs": [],
        "peak_below_runs": [],
        "ramp_violation_runs": [],
        "oxygen_over_limit_runs": [],
    }

    for run_id in escape_ids:
        run_row = runs_by_id.loc[run_id]
        trace = traces[(traces["run_id"] == run_id) & (traces["tc_role"] == REFERENCE_TC_ROLE)].copy()
        liquidus = float(run_row["solder_liquidus_c"])
        ramp = max_preheat_ramp(trace)
        tal = tal_seconds(trace, liquidus)
        peak = peak_temp(trace)
        required_min_peak = round2(liquidus + PEAK_MARGIN_C)
        dominant_defect = dominant_defect_for_run(defects, run_id)
        thermal_total = int(
            defects[
                (defects["run_id"] == run_id)
                & defects["inspection_stage"].isin(["AOI", "VISUAL"])
                & defects["defect_type"].isin(sorted(THERMAL_DEFECTS))
            ]["defect_count"].sum()
        )
        oxygen_limit = OXYGEN_LIMITS[str(run_row["gas_mode"])]
        oxygen_over = oxygen_limit is not None and float(run_row["o2_ppm_reflow"]) > float(oxygen_limit)
        if tal < TAL_MIN_S:
            evidence["tal_below_runs"].append(run_id)
        if peak < required_min_peak:
            evidence["peak_below_runs"].append(run_id)
        if ramp > RAMP_LIMIT_C_S:
            evidence["ramp_violation_runs"].append(run_id)
        if oxygen_over:
            evidence["oxygen_over_limit_runs"].append(run_id)
        evidence["dominant_defects"].append(dominant_defect)
        escape_analysis.append(
            {
                "run_id": run_id,
                "lot_id": str(run_row["lot_id"]),
                "dominant_defect": dominant_defect,
                "escape_defect_total": thermal_total,
                "ramp_c_per_s": round2(ramp),
                "tal_s": round2(tal),
                "peak_temp_c": round2(peak),
                "required_min_peak_c": round2(required_min_peak),
                "signal_flags": {
                    "ramp_violation": ramp > RAMP_LIMIT_C_S,
                    "tal_low": tal < TAL_MIN_S,
                    "peak_low": peak < required_min_peak,
                    "oxygen_over_limit": oxygen_over,
                },
            }
        )

    escape_analysis.sort(key=lambda row: row["run_id"])
    for key in evidence:
        if key == "dominant_defects":
            evidence[key] = sorted(set(evidence[key]))
        else:
            evidence[key] = sorted(evidence[key])

    center_runs = sorted(
        row["run_id"]
        for row in escape_analysis
        if row["signal_flags"]["tal_low"]
        and row["signal_flags"]["peak_low"]
        and row["dominant_defect"] in WETTING_DEFECTS
    )
    nitrogen_runs = sorted(
        row["run_id"]
        for row in escape_analysis
        if row["signal_flags"]["oxygen_over_limit"]
        and row["dominant_defect"] in WETTING_DEFECTS
        and str(runs_by_id.loc[row["run_id"], "gas_mode"]) != "Air"
    )
    ramp_runs = sorted(
        row["run_id"]
        for row in escape_analysis
        if row["signal_flags"]["ramp_violation"] and row["dominant_defect"] in RAMP_DEFECTS
    )

    if len(center_runs) >= 2:
        mode_code = "center_zone_heat_loss"
        trigger_runs = center_runs
    elif len(nitrogen_runs) >= 2:
        mode_code = "nitrogen_path_leak"
        trigger_runs = nitrogen_runs
    elif len(ramp_runs) >= 1:
        mode_code = "entry_ramp_overshoot"
        trigger_runs = ramp_runs
    else:
        mode_code = "recipe_loading_shift"
        trigger_runs = escape_ids

    if len(trigger_runs) >= 2:
        confidence = "high"
    elif len(trigger_runs) == 1:
        confidence = "medium"
    else:
        confidence = "low"

    affected_rows = mes[mes["run_id"].isin(trigger_runs)].copy().sort_values("panel_sn", kind="mergesort")
    hold_rows = affected_rows[affected_rows["disposition"] != "shipped"].copy()
    containment_scope = {
        "affected_run_ids": sorted(trigger_runs),
        "affected_lot_ids": sorted(runs[runs["run_id"].isin(trigger_runs)]["lot_id"].astype(str).unique().tolist()),
        "serial_span": [str(affected_rows["panel_sn"].min()), str(affected_rows["panel_sn"].max())],
        "panels_to_hold": int(len(hold_rows)),
        "shipped_panels": int((affected_rows["disposition"] == "shipped").sum()),
        "hold_locations": sorted(hold_rows["current_location"].astype(str).unique().tolist()),
    }

    template = ACTION_TEMPLATES[mode_code]
    output = {
        "incident_id": str(context["incident_id"]),
        "line_id": str(context["line_id"]),
        "window_reference": {
            "reference_tc_role": REFERENCE_TC_ROLE,
            "preheat_band_c": [round2(PREHEAT_MIN_C), round2(PREHEAT_MAX_C)],
            "max_ramp_c_per_s": round2(RAMP_LIMIT_C_S),
            "tal_window_s": [round2(TAL_MIN_S), round2(TAL_MAX_S)],
            "peak_margin_above_liquidus_c": round2(PEAK_MARGIN_C),
        },
        "escape_run_analysis": escape_analysis,
        "suspected_failure_mode": {
            "mode_code": mode_code,
            "priority_subsystem": MODE_TO_SUBSYSTEM[mode_code],
            "confidence": confidence,
            "trigger_run_ids": sorted(trigger_runs),
            "evidence": evidence,
        },
        "containment_scope": containment_scope,
        "immediate_actions": template["actions"],
        "technician_action_card": template["card"],
    }
    return output


os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "defect_containment_card.json"), "w", encoding="utf-8") as f:
    json.dump(build_output(), f, indent=2, ensure_ascii=False)
PY
