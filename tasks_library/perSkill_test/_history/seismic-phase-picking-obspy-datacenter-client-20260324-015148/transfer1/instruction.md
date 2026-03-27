A local seismic inventory mirror is bundled in this task. Start `/root/tools/seismic_archive_service.py` with `/root/data/service_dataset.json` on port `18080`, then query `http://127.0.0.1:18080`.

The mirror is intentionally minimal and does not publish discovery documents.

For each station query in `/root/requests/station_queries.csv`, retrieve the matching channel metadata and write `/root/transfer1_station_channel_audit.csv`.

Requirements:
- output columns must be:
  `request_id`, `station_id`, `channel_id`, `sample_rate_hz`, `start_date`, `end_date`
- `station_id` must use `NET.STA`
- `channel_id` must use `NET.STA.LOC.CHA`, and use `--` when the location code is blank
- if a channel has no end date, write `open`
- sort rows by `request_id`, then `channel_id`
- format `sample_rate_hz` with exactly 1 decimal place
