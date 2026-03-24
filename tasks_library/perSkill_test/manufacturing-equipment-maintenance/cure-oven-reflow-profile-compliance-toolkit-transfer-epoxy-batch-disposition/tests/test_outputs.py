import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

APP_ROOT = os.environ.get("APP_ROOT", "/app")
OUT_PATH = os.path.join(APP_ROOT, "output", "cure_batch_disposition.csv")
BATCH_LOG = os.path.join(APP_ROOT, "data", "batch_log.csv")
TC_CURVES = os.path.join(APP_ROOT, "data", "embedded_tc_curves.csv")

WARMUP_MIN_C = 60.0
WARMUP_MAX_C = 120.0
WARMUP_RAMP_LIMIT_C_PER_MIN = 1.40
MIN_CURE_TEMP_C = 150.0
MAX_EFFECTIVE_HOLD_TEMP_C = 162.0
EFFECTIVE_HOLD_MIN_S = 600.0
EFFECTIVE_HOLD_MAX_S = 840.0
RELEASE_OVERSHOOT_LIMIT_C = 3.0
REBAKE_OVERSHOOT_LIMIT_C = 1.5
PEAK_UNIFORMITY_LIMIT_C = 4.0
REBAKE_PROFILE = "RBK-150C-12M"
REASON_ORDER = [
    "warmup_ramp_high",
    "effective_hold_short",
    "effective_hold_long",
    "peak_overshoot_high",
    "uniformity_exceeds_limit",
    "door_open_alarm",
    "rebake_not_allowed",
]
EXPECTED_COLUMNS = [
    "batch_id",
    "product_code",
    "hold_limiting_tc_id",
    "hottest_tc_id",
    "coolest_peak_tc_id",
    "max_warmup_ramp_c_per_min",
    "effective_hold_s",
    "peak_overshoot_c",
    "peak_uniformity_c",
    "disposition",
    "reason_codes",
    "rebake_profile",
]


def round2(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return float(round(value, 2))


def load_output() -> pd.DataFrame:
    assert os.path.exists(OUT_PATH), f"Missing file: {OUT_PATH}"
    frame = pd.read_csv(OUT_PATH, keep_default_na=False)
    assert not frame.empty, "Output CSV is empty"
    return frame


def max_warmup_ramp(group: pd.DataFrame) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    best = None
    for idx in range(1, len(group)):
        t0 = float(group.iloc[idx - 1]["time_s"])
        t1 = float(group.iloc[idx]["time_s"])
        y0 = float(group.iloc[idx - 1]["temp_c"])
        y1 = float(group.iloc[idx]["temp_c"])
        if t1 <= t0:
            continue
        if WARMUP_MIN_C <= y0 <= WARMUP_MAX_C and WARMUP_MIN_C <= y1 <= WARMUP_MAX_C:
            slope = (y1 - y0) / (t1 - t0) * 60.0
            best = slope if best is None else max(best, slope)
    return round2(best)


def effective_hold_seconds(group: pd.DataFrame) -> Optional[float]:
    group = group.sort_values("time_s", kind="mergesort")
    total = 0.0
    seen = False
    for idx in range(1, len(group)):
        t0 = float(group.iloc[idx - 1]["time_s"])
        t1 = float(group.iloc[idx]["time_s"])
        y0 = float(group.iloc[idx - 1]["temp_c"])
        y1 = float(group.iloc[idx]["temp_c"])
        if t1 <= t0:
            continue
        seen = True
        points: List[Tuple[float, float]] = [(t0, y0), (t1, y1)]
        for threshold in (MIN_CURE_TEMP_C, MAX_EFFECTIVE_HOLD_TEMP_C):
            crosses = (y0 - threshold) * (y1 - threshold) < 0
            if crosses and y1 != y0:
                fraction = (threshold - y0) / (y1 - y0)
                points.append((t0 + fraction * (t1 - t0), threshold))
        points.sort(key=lambda item: item[0])
        for (ta, ya), (tb, yb) in zip(points, points[1:]):
            mid_temp = (ya + yb) / 2.0
            if MIN_CURE_TEMP_C <= mid_temp <= MAX_EFFECTIVE_HOLD_TEMP_C:
                total += tb - ta
    return None if not seen else round2(total)


def expected_output() -> pd.DataFrame:
    batch_log = pd.read_csv(BATCH_LOG)
    tc = pd.read_csv(TC_CURVES)
    batch_log["batch_id"] = batch_log["batch_id"].astype(str)
    batch_log["product_code"] = batch_log["product_code"].astype(str)
    batch_log["rebake_allowed"] = batch_log["rebake_allowed"].astype(str)
    tc["batch_id"] = tc["batch_id"].astype(str)
    tc["tc_id"] = tc["tc_id"].astype(str)

    rows: List[Dict[str, Any]] = []
    for _, batch in batch_log.sort_values("batch_id", kind="mergesort").iterrows():
        batch_id = str(batch["batch_id"])
        batch_tc = tc[tc["batch_id"] == batch_id]
        ramp_items = []
        hold_items = []
        peak_items = []
        for tc_id, group in batch_tc.groupby("tc_id", sort=False):
            ramp_items.append((max_warmup_ramp(group), str(tc_id)))
            hold_items.append((effective_hold_seconds(group), str(tc_id)))
            peak_items.append((round2(float(group["temp_c"].max())), str(tc_id)))

        valid_ramps = [(value, tc_id) for value, tc_id in ramp_items if value is not None]
        valid_holds = [(value, tc_id) for value, tc_id in hold_items if value is not None]
        max_ramp_value, _ = sorted(valid_ramps, key=lambda item: (-item[0], item[1]))[0]
        effective_hold_s, hold_tc_id = sorted(valid_holds, key=lambda item: (item[0], item[1]))[0]
        hottest_peak_c, hottest_tc_id = sorted(peak_items, key=lambda item: (-item[0], item[1]))[0]
        coolest_peak_c, coolest_peak_tc_id = sorted(peak_items, key=lambda item: (item[0], item[1]))[0]

        peak_overshoot_c = round2(max(0.0, hottest_peak_c - float(batch["target_peak_c"])))
        peak_uniformity_c = round2(hottest_peak_c - coolest_peak_c)

        reasons: List[str] = []
        if max_ramp_value > WARMUP_RAMP_LIMIT_C_PER_MIN:
            reasons.append("warmup_ramp_high")
        if effective_hold_s < EFFECTIVE_HOLD_MIN_S:
            reasons.append("effective_hold_short")
        if effective_hold_s > EFFECTIVE_HOLD_MAX_S:
            reasons.append("effective_hold_long")
        if peak_overshoot_c > RELEASE_OVERSHOOT_LIMIT_C:
            reasons.append("peak_overshoot_high")
        if peak_uniformity_c > PEAK_UNIFORMITY_LIMIT_C:
            reasons.append("uniformity_exceeds_limit")
        if int(batch["door_open_alarm"]) != 0:
            reasons.append("door_open_alarm")

        rebake_eligible = (
            reasons == ["effective_hold_short"]
            and str(batch["rebake_allowed"]).lower() == "yes"
            and int(batch["rebake_count"]) == 0
            and int(batch["door_open_alarm"]) == 0
            and max_ramp_value <= WARMUP_RAMP_LIMIT_C_PER_MIN
            and peak_overshoot_c <= REBAKE_OVERSHOOT_LIMIT_C
            and peak_uniformity_c <= PEAK_UNIFORMITY_LIMIT_C
        )

        if not reasons:
            disposition = "release"
            rebake_profile = ""
        elif rebake_eligible:
            disposition = "rebake"
            rebake_profile = REBAKE_PROFILE
        else:
            disposition = "hold"
            rebake_profile = ""
            if "effective_hold_short" in reasons:
                reasons.append("rebake_not_allowed")

        rows.append(
            {
                "batch_id": batch_id,
                "product_code": str(batch["product_code"]),
                "hold_limiting_tc_id": hold_tc_id,
                "hottest_tc_id": hottest_tc_id,
                "coolest_peak_tc_id": coolest_peak_tc_id,
                "max_warmup_ramp_c_per_min": round2(max_ramp_value),
                "effective_hold_s": round2(effective_hold_s),
                "peak_overshoot_c": peak_overshoot_c,
                "peak_uniformity_c": peak_uniformity_c,
                "disposition": disposition,
                "reason_codes": "|".join(code for code in REASON_ORDER if code in reasons),
                "rebake_profile": rebake_profile,
            }
        )
    return pd.DataFrame(rows, columns=EXPECTED_COLUMNS)


def test_output_schema_and_sorting() -> None:
    output = load_output()
    assert output.columns.tolist() == EXPECTED_COLUMNS
    assert output["batch_id"].tolist() == sorted(output["batch_id"].tolist())


def test_output_matches_expected_values() -> None:
    output = load_output()
    expected = expected_output()
    assert len(output) == len(expected)

    float_columns = [
        "max_warmup_ramp_c_per_min",
        "effective_hold_s",
        "peak_overshoot_c",
        "peak_uniformity_c",
    ]
    text_columns = [
        "batch_id",
        "product_code",
        "hold_limiting_tc_id",
        "hottest_tc_id",
        "coolest_peak_tc_id",
        "disposition",
        "reason_codes",
        "rebake_profile",
    ]

    output = output.reset_index(drop=True)
    expected = expected.reset_index(drop=True)
    for idx in range(len(expected)):
        for column in text_columns:
            assert str(output.at[idx, column]) == str(expected.at[idx, column]), (idx, column)
        for column in float_columns:
            assert round2(output.at[idx, column]) == round2(expected.at[idx, column]), (idx, column)


def test_reason_codes_and_rebake_profile_rules() -> None:
    output = load_output()
    for _, row in output.iterrows():
        reason_codes = str(row["reason_codes"])
        reasons = [] if reason_codes == "" else reason_codes.split("|")
        assert reasons == [code for code in REASON_ORDER if code in reasons]
        if str(row["disposition"]) == "rebake":
            assert reasons == ["effective_hold_short"]
            assert str(row["rebake_profile"]) == REBAKE_PROFILE
        else:
            assert str(row["rebake_profile"]) == ""
