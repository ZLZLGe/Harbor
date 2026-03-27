A local seismic bulletin mirror is bundled in this task. Start `/root/tools/seismic_archive_service.py` with `/root/data/service_dataset.json` on port `18080`, then query `http://127.0.0.1:18080`.

The mirror is intentionally minimal and does not publish discovery documents.

For each request in `/root/requests/event_windows.csv`, retrieve the matching events and write `/root/transfer2_event_digest.json`.

Requirements:
- the output must be a JSON array, preserving the input request order
- each object must contain:
  `request_id`, `event_count`, `event_ids`, `max_magnitude`, `mean_depth_km`, `largest_event_place`
- `event_ids` must be sorted by origin time ascending
- round `mean_depth_km` to 3 decimal places
