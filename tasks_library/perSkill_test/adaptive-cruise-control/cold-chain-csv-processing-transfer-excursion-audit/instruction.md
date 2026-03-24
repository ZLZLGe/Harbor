Create `shipment_excursion_audit.csv` from the two CSV inputs in the environment.

Inputs:
- `shipment_thresholds.csv` has one row per shipment with the allowed maximum temperature in Celsius.
- `shipment_temperature_log.csv` has minute-level logger data with columns `shipment_id`, `timestamp`, `door_open`, and `temperature_c`.

Output requirements:
- Write exactly one CSV named `shipment_excursion_audit.csv`.
- Use these columns in this exact order:
  `shipment_id,excursion_start,excursion_end,duration_minutes,peak_temperature_c,door_open_during_excursion`
- A temperature excursion is any recorded sample where `temperature_c` is strictly greater than that shipment's allowed maximum temperature.
- Blank `temperature_c` cells are missing thermometer samples. Ignore the missing row itself, but do not let it split an ongoing excursion if the surrounding valid breach samples belong to the same continuous incident window.
- Group excursion rows into incident windows separately for each `shipment_id`.
- End an incident when you reach a valid non-breach sample for that shipment.
- `excursion_start` and `excursion_end` should be the first and last breach timestamps in the window.
- `duration_minutes` should be the inclusive minute span from start to end. For example, a window from `08:01` through `08:04` has duration `4`.
- `peak_temperature_c` is the highest recorded temperature within the window.
- `door_open_during_excursion` should be `yes` if any row inside the incident window has `door_open = Y`, otherwise `no`.
- Sort the final CSV by `shipment_id`, then by `excursion_start`.

Do not add extra files or extra columns.
