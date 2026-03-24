You are auditing one highway ACC telemetry run instead of building a simulator.

Input file available in `/root`:
- `highway_trip.csv`

Create `build_mode_audit.py` and run it. The script must read `highway_trip.csv` and produce:
- `acc_mode_audit.csv`
- `audit_summary.json`

Do not modify `highway_trip.csv`.

`highway_trip.csv` columns:
- `time_s`
- `road_phase`
- `ego_speed_mps`
- `lead_speed_mps`
- `lead_gap_m`

Use these fixed ACC audit rules:
- Safe gap formula: `safe_gap_m = ego_speed_mps * 1.5 + 10.0`
- Lead vehicle is considered present only when both `lead_speed_mps` and `lead_gap_m` are non-empty
- `closing_speed_mps = ego_speed_mps - lead_speed_mps` when lead is present, otherwise leave it blank
- `gap_margin_m = lead_gap_m - safe_gap_m` when lead is present, otherwise leave it blank
- `ttc_s = lead_gap_m / closing_speed_mps` only when lead is present and `closing_speed_mps > 0`; otherwise leave it blank
- `mode = cruise` when lead is missing
- `mode = emergency` when `ttc_s` exists and is strictly less than `3.0`
- Otherwise `mode = follow`
- `gap_flag = missing_lead` when lead is missing, `tight` when `gap_margin_m < 0`, otherwise `safe`

Write `acc_mode_audit.csv` with exactly these columns in this exact order:
1. `time_s`
2. `road_phase`
3. `ego_speed_mps`
4. `lead_speed_mps`
5. `lead_gap_m`
6. `lead_present`
7. `closing_speed_mps`
8. `safe_gap_m`
9. `gap_margin_m`
10. `ttc_s`
11. `mode`
12. `gap_flag`

Formatting requirements:
- Keep the same number of rows and the same row order as the input CSV
- Copy the original telemetry columns through unchanged
- `lead_present` must be written as lowercase `true` or `false`
- Round computed numeric columns to 3 decimals: `closing_speed_mps`, `safe_gap_m`, `gap_margin_m`, `ttc_s`
- Leave unavailable computed values blank in the CSV

Write `audit_summary.json` with exactly these top-level keys:
- `rows_total`
- `lead_present_rows`
- `lead_missing_rows`
- `mode_counts`
- `gap_flag_counts`
- `min_ttc_s`
- `min_observed_gap_m`
- `max_gap_deficit_m`
- `first_emergency_time_s`

Summary requirements:
- `mode_counts` must contain `cruise`, `follow`, and `emergency`
- `gap_flag_counts` must contain `missing_lead`, `tight`, and `safe`
- Round numeric summary metrics to 3 decimals
