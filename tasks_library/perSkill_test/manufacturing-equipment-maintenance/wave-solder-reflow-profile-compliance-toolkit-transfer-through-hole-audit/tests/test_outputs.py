import math
import os
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

APP_ROOT = os.environ.get("APP_ROOT", "/app")
OUT_PATH = os.path.join(APP_ROOT, "output", "wave_solder_profile_audit.yaml")
HANDBOOK_PATH = os.path.join(APP_ROOT, "data", "wave_solder_handbook.pdf")
LOT_PATH = os.path.join(APP_ROOT, "data", "lot_manifest.csv")
TC_PATH = os.path.join(APP_ROOT, "data", "wave_thermocouples.csv")
SPEED_PATH = os.path.join(APP_ROOT, "data", "line_speed_log.csv")
DEFECT_PATH = os.path.join(APP_ROOT, "data", "defect_ledger.csv")

PREHEAT_MIN_C = 90.0
PREHEAT_MAX_C = 140.0
MAX_PREHEAT_RAMP_C_PER_S = 1.6
ENTRY_TEMP_MIN_C = 100.0
ENTRY_TEMP_MAX_C = 115.0
CONTACT_TIME_THRESHOLD_C = 240.0
CONTACT_TIME_MIN_S = 3.0
CONTACT_TIME_MAX_S = 4.0
EFFECTIVE_WAVE_CONTACT_LENGTH_CM = 4.8
SPEED_MIN_CM_MIN = 72.0
SPEED_MAX_CM_MIN = 96.0
TARGET_ENTRY_TEMP_C = 107.5
TARGET_CONTACT_TIME_S = 3.5
TARGET_SPEED_CM_MIN = 84.0
FAILURE_REASON_ORDER = [
    "preheat_ramp_exceeds_limit",
    "entry_temp_out_of_window",
    "contact_time_out_of_window",
    "speed_out_of_window",
    "bridging_present",
    "insufficient_fill_present",
]


def load_yaml(path: str) -> Any:
    assert os.path.exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    assert data.strip(), f"Empty file: {path}"
    return yaml.safe_load(data)


def round2(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return float(round(value, 2))


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
    return round2(best)


def time_above_threshold(group: pd.DataFrame) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    total = 0.0
    seen = False
    times = group["time_s"].astype(float).tolist()
    temps = group["temp_c"].astype(float).tolist()
    for idx in range(1, len(group)):
        t0 = times[idx - 1]
        t1 = times[idx]
        y0 = temps[idx - 1]
        y1 = temps[idx]
        if t1 <= t0:
            continue
        seen = True
        if y0 > CONTACT_TIME_THRESHOLD_C and y1 > CONTACT_TIME_THRESHOLD_C:
            total += t1 - t0
            continue
        crosses = (y0 <= CONTACT_TIME_THRESHOLD_C < y1) or (y1 <= CONTACT_TIME_THRESHOLD_C < y0)
        if crosses and y1 != y0:
            fraction = (CONTACT_TIME_THRESHOLD_C - y0) / (y1 - y0)
            t_cross = t0 + fraction * (t1 - t0)
            if y0 <= CONTACT_TIME_THRESHOLD_C and y1 > CONTACT_TIME_THRESHOLD_C:
                total += t1 - t_cross
            else:
                total += t_cross - t0
    if not seen:
        return None
    return round2(total)


def sorted_failure_reasons(failures: List[str]) -> List[str]:
    order = {code: idx for idx, code in enumerate(FAILURE_REASON_ORDER)}
    return sorted(failures, key=lambda code: order[code])


def expected_output() -> Dict[str, Any]:
    lots = pd.read_csv(LOT_PATH).sort_values(["lot_id"], kind="mergesort")
    tc = pd.read_csv(TC_PATH).sort_values(["lot_id", "tc_id", "record_type", "time_s"], kind="mergesort")
    speed = pd.read_csv(SPEED_PATH).sort_values(["lot_id", "stamp_s"], kind="mergesort")
    defects = pd.read_csv(DEFECT_PATH).sort_values(["lot_id", "defect_type"], kind="mergesort")

    lot_rows: List[Dict[str, Any]] = []
    for _, lot in lots.iterrows():
        lot_id = str(lot["lot_id"])
        lot_tc = tc[tc["lot_id"] == lot_id]

        preheat = lot_tc[lot_tc["sensor_group"] == "top_preheat"]
        ramp_values = [
            value
            for _, group in preheat.groupby("tc_id", sort=False)
            for value in [max_preheat_ramp(group)]
            if value is not None
        ]
        max_ramp = round2(max(ramp_values)) if ramp_values else None

        entry = lot_tc[(lot_tc["record_type"] == "entry_snapshot") & (lot_tc["sensor_group"] == "entry_top")]
        entry_choices = sorted(
            [(float(row["temp_c"]), str(row["tc_id"])) for _, row in entry.iterrows()],
            key=lambda item: (item[0], item[1]),
        )
        board_entry_temp_c = round2(entry_choices[0][0]) if entry_choices else None
        entry_sensor_id = entry_choices[0][1] if entry_choices else None

        wave = lot_tc[(lot_tc["record_type"] == "wave_trace") & (lot_tc["sensor_group"] == "wave_contact")]
        contact_choices: List[Tuple[float, str]] = []
        for tc_id, group in wave.groupby("tc_id", sort=False):
            value = time_above_threshold(group)
            if value is not None:
                contact_choices.append((float(value), str(tc_id)))
        contact_choices.sort(key=lambda item: (-item[0], item[1]))
        contact_time_s = round2(contact_choices[0][0]) if contact_choices else None
        contact_sensor_id = contact_choices[0][1] if contact_choices else None

        actual_speed_cm_min = round2(median(speed[speed["lot_id"] == lot_id]["speed_cm_min"].astype(float).tolist()))

        bridge_count = int(defects[(defects["lot_id"] == lot_id) & (defects["defect_type"] == "bridge")]["count"].sum())
        insufficient_fill_count = int(
            defects[(defects["lot_id"] == lot_id) & (defects["defect_type"] == "insufficient_fill")]["count"].sum()
        )

        thermal_pass = (
            max_ramp is not None
            and max_ramp <= MAX_PREHEAT_RAMP_C_PER_S
            and board_entry_temp_c is not None
            and ENTRY_TEMP_MIN_C <= board_entry_temp_c <= ENTRY_TEMP_MAX_C
            and contact_time_s is not None
            and CONTACT_TIME_MIN_S <= contact_time_s <= CONTACT_TIME_MAX_S
        )
        speed_pass = SPEED_MIN_CM_MIN <= actual_speed_cm_min <= SPEED_MAX_CM_MIN
        defect_pass = bridge_count == 0 and insufficient_fill_count == 0

        failures: List[str] = []
        if max_ramp is None or max_ramp > MAX_PREHEAT_RAMP_C_PER_S:
            failures.append("preheat_ramp_exceeds_limit")
        if board_entry_temp_c is None or not (ENTRY_TEMP_MIN_C <= board_entry_temp_c <= ENTRY_TEMP_MAX_C):
            failures.append("entry_temp_out_of_window")
        if contact_time_s is None or not (CONTACT_TIME_MIN_S <= contact_time_s <= CONTACT_TIME_MAX_S):
            failures.append("contact_time_out_of_window")
        if actual_speed_cm_min is None or not (SPEED_MIN_CM_MIN <= actual_speed_cm_min <= SPEED_MAX_CM_MIN):
            failures.append("speed_out_of_window")
        if bridge_count > 0:
            failures.append("bridging_present")
        if insufficient_fill_count > 0:
            failures.append("insufficient_fill_present")

        lot_rows.append(
            {
                "lot_id": lot_id,
                "profile_id": str(lot["profile_id"]),
                "entry_sensor_id": entry_sensor_id,
                "contact_sensor_id": contact_sensor_id,
                "max_preheat_ramp_c_per_s": max_ramp,
                "board_entry_temp_c": board_entry_temp_c,
                "contact_time_s": contact_time_s,
                "actual_speed_cm_min": actual_speed_cm_min,
                "bridge_count": bridge_count,
                "insufficient_fill_count": insufficient_fill_count,
                "thermal_status": "pass" if thermal_pass else "fail",
                "speed_status": "pass" if speed_pass else "fail",
                "defect_status": "pass" if defect_pass else "fail",
                "audit_status": "pass" if thermal_pass and speed_pass and defect_pass else "fail",
                "failure_reasons": sorted_failure_reasons(failures),
            }
        )

    lot_rows.sort(key=lambda row: row["lot_id"])
    qualified_lot_ids = [row["lot_id"] for row in lot_rows if row["audit_status"] == "pass"]
    blocked_lot_ids = [row["lot_id"] for row in lot_rows if row["audit_status"] == "fail"]

    recommended_profiles: List[Dict[str, Any]] = []
    for profile_id, group in lots.groupby("profile_id", sort=False):
        passing = [row for row in lot_rows if row["profile_id"] == str(profile_id) and row["audit_status"] == "pass"]
        if not passing:
            continue
        average_entry_temp_c = round2(sum(float(row["board_entry_temp_c"]) for row in passing) / len(passing))
        average_contact_time_s = round2(sum(float(row["contact_time_s"]) for row in passing) / len(passing))
        average_speed_cm_min = round2(sum(float(row["actual_speed_cm_min"]) for row in passing) / len(passing))
        manifest = group.iloc[0]
        recommended_profiles.append(
            {
                "profile_id": str(profile_id),
                "preheater_top_sp_c": round2(float(manifest["preheater_top_sp_c"])),
                "chip_wave_height_mm": round2(float(manifest["chip_wave_height_mm"])),
                "lambda_wave_height_mm": round2(float(manifest["lambda_wave_height_mm"])),
                "lot_count": len(passing),
                "qualified_lot_ids": sorted(row["lot_id"] for row in passing),
                "average_entry_temp_c": average_entry_temp_c,
                "average_contact_time_s": average_contact_time_s,
                "average_speed_cm_min": average_speed_cm_min,
                "recommended_speed_cm_min": average_speed_cm_min,
            }
        )

    recommended_profiles.sort(
        key=lambda row: (
            -int(row["lot_count"]),
            abs(float(row["average_entry_temp_c"]) - TARGET_ENTRY_TEMP_C),
            abs(float(row["average_contact_time_s"]) - TARGET_CONTACT_TIME_S),
            abs(float(row["average_speed_cm_min"]) - TARGET_SPEED_CM_MIN),
            row["profile_id"],
        )
    )

    return {
        "line_id": "WS-7",
        "handbook_limits": {
            "preheat_temp_min_c": PREHEAT_MIN_C,
            "preheat_temp_max_c": PREHEAT_MAX_C,
            "max_preheat_ramp_c_per_s": MAX_PREHEAT_RAMP_C_PER_S,
            "entry_temp_min_c": ENTRY_TEMP_MIN_C,
            "entry_temp_max_c": ENTRY_TEMP_MAX_C,
            "contact_time_threshold_c": CONTACT_TIME_THRESHOLD_C,
            "contact_time_min_s": CONTACT_TIME_MIN_S,
            "contact_time_max_s": CONTACT_TIME_MAX_S,
            "effective_wave_contact_length_cm": EFFECTIVE_WAVE_CONTACT_LENGTH_CM,
            "speed_min_cm_min": SPEED_MIN_CM_MIN,
            "speed_max_cm_min": SPEED_MAX_CM_MIN,
            "target_entry_temp_c": TARGET_ENTRY_TEMP_C,
            "target_contact_time_s": TARGET_CONTACT_TIME_S,
            "target_speed_cm_min": TARGET_SPEED_CM_MIN,
            "entry_sensor_rule": "lowest_entry_temp_then_smallest_tc_id",
            "contact_sensor_rule": "longest_time_above_threshold_then_smallest_tc_id",
        },
        "qualified_lot_ids": qualified_lot_ids,
        "blocked_lot_ids": blocked_lot_ids,
        "best_profile_id": recommended_profiles[0]["profile_id"] if recommended_profiles else None,
        "lots": lot_rows,
        "recommended_profiles": recommended_profiles,
    }


def test_handbook_asset_mentions_expected_rules():
    with open(HANDBOOK_PATH, "r", encoding="utf-8") as handle:
        handbook = handle.read()
    assert "90.0 C to 140.0 C" in handbook
    assert "100.0 C to 115.0 C" in handbook
    assert "3.00 s to 4.00 s" in handbook
    assert "72.00" in handbook and "96.00" in handbook


def test_output_exists_and_has_required_top_level_keys():
    out = load_yaml(OUT_PATH)
    assert isinstance(out, dict)
    assert list(out.keys()) == [
        "line_id",
        "handbook_limits",
        "qualified_lot_ids",
        "blocked_lot_ids",
        "best_profile_id",
        "lots",
        "recommended_profiles",
    ]


def test_output_matches_expected_audit_packet():
    out = load_yaml(OUT_PATH)
    expected = expected_output()

    assert out["line_id"] == expected["line_id"]
    assert out["handbook_limits"] == expected["handbook_limits"]
    assert out["qualified_lot_ids"] == expected["qualified_lot_ids"]
    assert out["blocked_lot_ids"] == expected["blocked_lot_ids"]
    assert out["best_profile_id"] == expected["best_profile_id"]

    lots = out["lots"]
    assert isinstance(lots, list)
    assert [row["lot_id"] for row in lots] == sorted(row["lot_id"] for row in lots)
    assert lots == expected["lots"]

    profiles = out["recommended_profiles"]
    assert isinstance(profiles, list)
    assert profiles == expected["recommended_profiles"]


def test_speed_window_is_consistent_with_contact_length_rule():
    out = load_yaml(OUT_PATH)
    limits = out["handbook_limits"]
    expected_speed_min = round2(EFFECTIVE_WAVE_CONTACT_LENGTH_CM / CONTACT_TIME_MAX_S * 60.0)
    expected_speed_max = round2(EFFECTIVE_WAVE_CONTACT_LENGTH_CM / CONTACT_TIME_MIN_S * 60.0)
    assert limits["speed_min_cm_min"] == expected_speed_min
    assert limits["speed_max_cm_min"] == expected_speed_max
