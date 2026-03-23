An operations video is provided at `/root/transfer1_source.mp4`.

Blocked windows are listed in:

- `/root/data/transfer1_remove_windows.json`

Create these outputs in `/root/`:

1. `transfer1_clean_cut.mp4`
2. `transfer1_redaction_report.json`

Rules:

1. Treat blocked windows as intervals to remove from the source timeline.
2. Merge overlapping blocked windows before computing the keep windows.
3. Build `transfer1_clean_cut.mp4` by concatenating all keep windows in ascending time order.
4. `transfer1_redaction_report.json` must include:
   - `source_video`
   - `output_video`
   - `source_duration_seconds`
   - `removed_windows_merged`
   - `keep_windows`
   - `removed_total_seconds`
   - `kept_total_seconds`
5. `kept_total_seconds` must equal `source_duration_seconds - removed_total_seconds` within normal rounding error.
