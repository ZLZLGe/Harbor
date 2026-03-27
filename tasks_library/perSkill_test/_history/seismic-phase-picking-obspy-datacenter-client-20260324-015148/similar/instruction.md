A local seismic archive mirror is bundled in this task. Start the provided service script at `/root/tools/seismic_archive_service.py` with `/root/data/service_dataset.json` on port `18080`, then query the mirror at `http://127.0.0.1:18080`.

The mirror is intentionally minimal and does not publish discovery documents.

Retrieve every waveform request listed in `/root/requests/waveform_requests.csv` and save:
- `/root/similar_waveform_metrics.csv`
- `/root/similar_waveform_summary.json`

Requirements:
- produce one row per retrieved trace
- `similar_waveform_metrics.csv` must contain exactly these columns:
  `request_id`, `trace_id`, `sample_count`, `peak_abs`, `mean_abs`, `rms`
- `trace_id` must use `NET.STA.LOC.CHA`, and use `--` when the location code is blank
- sort the CSV rows by `request_id`
- round all floating-point metrics in the CSV to 6 decimal places
- `similar_waveform_summary.json` must contain:
  `request_count`, `trace_count`, `largest_peak_trace`, `largest_peak_value`
