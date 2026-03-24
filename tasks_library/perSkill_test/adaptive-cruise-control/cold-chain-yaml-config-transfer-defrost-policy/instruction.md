You need to prepare an updated cold-room defrost plan from the nested rules in `freezer_policy.yaml` and the hourly readings in `temperature_log.csv`.

The log covers one day for four freezers. Treat a row as part of an abnormal period when either:
- `temp_c` is warmer than that freezer group's `max_temp_c`
- `alarm_code` is `HIGH_TEMP`

Rows for the same freezer belong to the same abnormal period when they are consecutive samples in the log. The sampling interval is given in the YAML file.

First, create `policy_transfer.py`. It must expose a function:

`build_defrost_policy(policy_path, log_path) -> tuple[dict, list[dict]]`

The returned tuple should contain:
- the full data structure that will be written to `defrost_policy.yaml`
- the row dictionaries that will be written to `anomaly_summary.csv`

Then run that logic to produce:
- `defrost_policy.yaml`
- `anomaly_summary.csv`

Rules for `defrost_policy.yaml`:
- Top-level keys must be `site`, `source_files`, and `policy_recommendations`.
- `source_files.policy` must be `freezer_policy.yaml`.
- `source_files.log` must be `temperature_log.csv`.
- Preserve freezer order from the YAML input.
- Each freezer entry under `policy_recommendations` must contain:
  - `group`
  - `schedule.interval_hours`
  - `schedule.duration_minutes`
  - `schedule.preferred_window`
  - `schedule.recommended_start`
  - `analysis.anomaly_periods`
  - `analysis.total_anomaly_hours`
  - `analysis.peak_temp_c`
  - `analysis.peak_excursion_c`
  - `analysis.door_open_hours`
  - `analysis.inspection_priority`
  - `analysis.trigger_codes`

Adjustment rules:
- Start from the freezer group's `defrost.base_interval_hours` and `defrost.base_duration_minutes`.
- `peak_excursion_c` is `max(0, peak_temp_c - max_temp_c)` rounded to 1 decimal place.
- Reduce the interval by 2 hours when `peak_excursion_c >= severe_excursion_delta_c`.
- Otherwise reduce the interval by 2 hours when `total_anomaly_hours >= long_event_hours`.
- Otherwise reduce the interval by 1 hour when `anomaly_periods >= repeat_event_threshold`.
- Never go below `defrost.min_interval_hours`.
- Add 5 minutes to the duration when `total_anomaly_hours >= long_event_hours`.
- Add 5 minutes to the duration when `door_open_hours >= door_open_extension_threshold`.
- Add 5 minutes to the duration when `peak_excursion_c >= severe_excursion_delta_c`.
- Never exceed `defrost.max_duration_minutes`.
- `preferred_window` is the alarm window that contains the most abnormal rows for that freezer. Break ties by the order the windows appear in the YAML file.
- `recommended_start` comes from that selected window.
- `inspection_priority` is `urgent` when `peak_excursion_c >= severe_excursion_delta_c`, `review` when that is false but either `anomaly_periods >= repeat_event_threshold` or `total_anomaly_hours >= long_event_hours`, otherwise `routine`.
- `trigger_codes` should list the distinct non-empty `alarm_code` values seen for that freezer in log order without duplicates.

Rules for `anomaly_summary.csv`:
- Use this exact column order:

```csv
freezer_id,group_name,start_time,end_time,duration_hours,peak_temp_c,door_open_hours,window_name,priority
```

- Write one row per abnormal period.
- Order rows first by freezer order from `equipment_groups.*.freezer_ids` in `freezer_policy.yaml`, then by abnormal-period `start_time` ascending within each freezer.
- `start_time` and `end_time` must use the original timestamp format from the log.
- `duration_hours` is the number of samples in that abnormal period because the log interval is 1 hour.
- `window_name` is the alarm window containing the period start time.
- `priority` should match the freezer's `inspection_priority`.

Keep `freezer_policy.yaml` and `temperature_log.csv` unchanged.
