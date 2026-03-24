Create `inverter_loss_summary.csv` from the inverter production CSV in the environment.

Input:
- `inverter_production.csv` contains 15-minute readings with columns `inverter_id,timestamp,actual_kwh,curtailment_flag,event_code`.

Output requirements:
- Write exactly one CSV named `inverter_loss_summary.csv`.
- Use these columns in this exact order:
  `inverter_id,interval_type,interval_start,interval_end,sample_count,baseline_kwh,estimated_lost_kwh,root_cause_label`
- Sort the final CSV by `inverter_id`, then by `interval_start`.
- Treat `timestamp` as already ordered within each inverter, but your logic should still work after sorting by `inverter_id` and `timestamp`.
- A valid baseline sample is a row for the same `inverter_id` where `actual_kwh` is present and `curtailment_flag = N`.
- A downtime interval is one or more consecutive rows for the same inverter where `actual_kwh` is blank and `curtailment_flag = N`.
- A curtailed interval is one or more consecutive rows for the same inverter where `curtailment_flag = Y` and `actual_kwh` is present.
- Ignore rows that are neither downtime nor curtailed-generation rows.
- For each interval, find the nearest previous valid baseline sample and the nearest next valid baseline sample for that same inverter. Use the arithmetic mean of those two readings as `baseline_kwh`.
- `sample_count` is the number of rows in the interval.
- For a downtime interval, `estimated_lost_kwh = baseline_kwh * sample_count`.
- For a curtailed interval, `estimated_lost_kwh` is the sum across the interval of `max(baseline_kwh - actual_kwh, 0)`.
- Round both `baseline_kwh` and `estimated_lost_kwh` to 2 decimal places in the output.
- Set `interval_type` to `downtime` or `curtailment`.
- `interval_start` and `interval_end` are the first and last timestamps in the interval.
- Map `event_code` to `root_cause_label` as follows:
  `maint -> planned_maintenance`
  `comms -> communications_outage`
  `grid -> grid_curtailment`
- Do not add extra columns or extra files.
