A panel rehearsal was reduced to short mic-check excerpts in:

- `/root/data/mic_check_segments.tsv`

Columns:

- `segment_id`
- `seat`
- `start_sec`
- `end_sec`
- `sig_1` through `sig_5`

Production notes confirm that the sequence contains exactly **4 recurring voices**. Use the signature columns to place every excerpt into a stable speaker bucket.

Write `/root/output/transfer2_room_rollup.json` with:

- `speaker_count`
- `total_duration_sec`
- `buckets`

Each item in `buckets` must include:

- `speaker_label`
- `segment_ids`
- `seats`
- `total_duration_sec`
- `first_seen_sec`

Keep buckets ordered by first appearance in the timeline.
