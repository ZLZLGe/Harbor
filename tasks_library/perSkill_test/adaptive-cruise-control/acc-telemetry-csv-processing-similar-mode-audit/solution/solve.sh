#!/bin/bash
set -euo pipefail

cat <<'PY' > /root/build_mode_audit.py
import json

import pandas as pd


def rounded(value):
    return round(float(value), 3)


df = pd.read_csv("/root/highway_trip.csv")

lead_present = df["lead_speed_mps"].notna() & df["lead_gap_m"].notna()
closing_speed = df["ego_speed_mps"] - df["lead_speed_mps"]
safe_gap = df["ego_speed_mps"] * 1.5 + 10.0
gap_margin = df["lead_gap_m"] - safe_gap
ttc = df["lead_gap_m"] / closing_speed
ttc = ttc.where(lead_present & (closing_speed > 0))

mode = pd.Series("follow", index=df.index)
mode = mode.where(~(ttc.notna() & (ttc < 3.0)), "emergency")
mode = mode.where(lead_present, "cruise")

gap_flag = pd.Series("safe", index=df.index)
gap_flag = gap_flag.where(gap_margin >= 0, "tight")
gap_flag = gap_flag.where(lead_present, "missing_lead")

audit = pd.DataFrame(
    {
        "time_s": df["time_s"],
        "road_phase": df["road_phase"],
        "ego_speed_mps": df["ego_speed_mps"],
        "lead_speed_mps": df["lead_speed_mps"],
        "lead_gap_m": df["lead_gap_m"],
        "lead_present": lead_present.map({True: "true", False: "false"}),
        "closing_speed_mps": closing_speed.where(lead_present).round(3),
        "safe_gap_m": safe_gap.round(3),
        "gap_margin_m": gap_margin.where(lead_present).round(3),
        "ttc_s": ttc.round(3),
        "mode": mode,
        "gap_flag": gap_flag,
    }
)
audit.to_csv("/root/acc_mode_audit.csv", index=False)

summary = {
    "rows_total": int(len(audit)),
    "lead_present_rows": int(lead_present.sum()),
    "lead_missing_rows": int((~lead_present).sum()),
    "mode_counts": {
        "cruise": int((audit["mode"] == "cruise").sum()),
        "follow": int((audit["mode"] == "follow").sum()),
        "emergency": int((audit["mode"] == "emergency").sum()),
    },
    "gap_flag_counts": {
        "missing_lead": int((audit["gap_flag"] == "missing_lead").sum()),
        "tight": int((audit["gap_flag"] == "tight").sum()),
        "safe": int((audit["gap_flag"] == "safe").sum()),
    },
    "min_ttc_s": rounded(audit["ttc_s"].dropna().min()),
    "min_observed_gap_m": rounded(df["lead_gap_m"].dropna().min()),
    "max_gap_deficit_m": rounded((-audit["gap_margin_m"].fillna(0)).clip(lower=0).max()),
    "first_emergency_time_s": rounded(audit.loc[audit["mode"] == "emergency", "time_s"].iloc[0]),
}

with open("/root/audit_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
PY

python3 /root/build_mode_audit.py
