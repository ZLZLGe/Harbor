A batch manifest and per-channel segment files are available under `/root/`.

Input manifest:

- `/root/channel_manifest.json`

Produce `/root/transfer3_trim_budget_report.csv` with columns:

1. `channel_id`
2. `total_segments`
3. `total_duration_seconds`
4. `budget_seconds`
5. `over_budget`
6. `rank`

Rules:

1. For each channel, merge all listed segment files into one timeline before calculating totals.
2. `total_segments` and `total_duration_seconds` come from the merged timeline.
3. `over_budget` is `yes` when `total_duration_seconds > budget_seconds`, otherwise `no`.
4. Sort rows by `total_duration_seconds` descending, then `channel_id` ascending.
5. `rank` starts at `1` after sorting.
