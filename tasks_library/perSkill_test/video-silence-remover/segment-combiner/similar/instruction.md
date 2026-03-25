Merge lecture opening and pause segments into a single removal list.

Inputs:
- `/root/data/opening.json`
- `/root/data/pauses.json`

Save:
- `/root/lecture_all_segments.json`
- `/root/lecture_segment_summary.json`

Requirements:
- use the segment-combiner skill to create the combined segments JSON
- in the summary JSON record `segment_count`, `total_duration_seconds`, `first_segment_start`, and `last_segment_end`
