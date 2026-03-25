The bundled clip `/root/input.mp4` has a fragmented activity draft in `/root/pickup_boundaries.tsv`.

Convert that draft into padded review cues and write `/root/pickup_cues.tsv`.

Rules:
- Read all rows from `/root/pickup_boundaries.tsv`.
- Sort by `start`.
- Merge neighboring rows when the next `start` is at most `0.25` seconds after the current `end`.
- After merging, drop any merged speech window shorter than `0.30` seconds.
- Expand every remaining speech window by `0.20` seconds before the start and `0.35` seconds after the end.
- Clamp padded windows to the `clip_duration_sec` in `/root/cue_config.json`.
- After padding, merge windows that overlap or touch.
- Round every numeric value to 3 decimals.

Write tab-separated output with this header:

```text
cue_id	start_sec	end_sec	duration_sec	source_segment_count	source_segments
```

`source_segments` must be a semicolon-separated list of the merged speech segment IDs that contributed to each cue.
