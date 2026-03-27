You need to draft rapid acquisition windows for three local earthquake notifications.

Start `/root/tools/seismic_archive_service.py` with `/root/data/service_dataset.json` on port `18080`, then query `http://127.0.0.1:18080`.

The mirror is intentionally minimal and does not publish discovery documents.

Use the event requests in `/root/requests/response_targets.csv` and write `/root/transfer3_response_plan.csv`.

Requirements:
- find the nearest matching station/channel for each event request
- output columns must be:
  `event_id`, `event_place`, `station_id`, `channel_id`, `distance_km`, `request_start`, `request_end`
- `station_id` must use `NET.STA`
- `channel_id` must use `NET.STA.LOC.CHA`, and use `--` when the location code is blank
- round `distance_km` to 3 decimal places
- `request_start` and `request_end` must be ISO timestamps in `YYYY-MM-DDTHH:MM:SS`
