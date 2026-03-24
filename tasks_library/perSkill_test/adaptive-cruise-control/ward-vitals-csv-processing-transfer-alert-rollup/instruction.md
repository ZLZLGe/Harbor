Create `patient_alert_windows.csv` from the monitor export `bedside_vitals.csv`.

Input details:
- `bedside_vitals.csv` contains `patient_id`, `timestamp`, `heart_rate_bpm`, `spo2_percent`, and `ward`.
- Blank `heart_rate_bpm` or `spo2_percent` cells are missing sensor readings.
- Treat timestamps as already ordered within each patient once parsed as datetimes.

Alert rules:
- Create alerts separately for each `patient_id`.
- `high_heart_rate` is any row where `heart_rate_bpm` is strictly greater than `120`.
- `low_spo2` is any row where `spo2_percent` is strictly less than `90`.
- Collapse consecutive alert rows for the same patient and the same alert type into one alert window.
- Missing readings for the relevant signal should be ignored and must not split an already active alert window.
- A valid non-alert reading for the relevant signal ends the active alert window.

Output requirements:
- Write exactly one CSV named `patient_alert_windows.csv`.
- Use these columns in this exact order:
  `patient_id,alert_type,alert_start,alert_end,extreme_value,recovery_time_minutes`
- `alert_start` and `alert_end` are the first and last alert timestamps in that window.
- `extreme_value` is the highest heart rate seen in a `high_heart_rate` window, and the lowest SpO2 seen in a `low_spo2` window.
- `recovery_time_minutes` is the number of whole minutes from `alert_end` to the first later valid non-alert reading for the same patient and same signal.
- If an alert never recovers before the file ends, leave `recovery_time_minutes` blank.
- Format timestamps as `YYYY-MM-DD HH:MM`.
- Sort the final CSV by `patient_id`, then `alert_start`, then `alert_type`.

Do not add extra files or extra columns.
