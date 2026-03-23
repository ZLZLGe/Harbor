Overnight dispatch snippets from one shift are stored in:

- `/root/data/dispatch_segments.csv`

Columns:

- `segment_id`
- `zone`
- `start_sec`
- `end_sec`
- `sig_1` through `sig_4`

Operations already confirmed that exactly **3 unique voices** appear in this shift. Use the signature columns to assign a stable `speaker_01`, `speaker_02`, `speaker_03` label to every segment.

Write these outputs:

1. `/root/output/transfer1_speaker_manifest.csv`
   - columns: `segment_id`, `zone`, `start_sec`, `end_sec`, `duration_sec`, `speaker_label`
   - preserve chronological order

2. `/root/output/transfer1_shift_totals.json`
   - include `speaker_count`
   - include `durations_sec`
   - include `segments_per_speaker`

Do not merge non-adjacent rows. Keep the label assignment consistent across the full file.
