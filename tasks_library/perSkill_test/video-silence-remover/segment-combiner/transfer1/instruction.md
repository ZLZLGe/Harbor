Merge compliance review segments into a single ordered removal list.

Inputs:
- `/root/data/intro.json`
- `/root/data/holds.json`
- `/root/data/handoff.json`

Save:
- `/root/compliance_all_segments.json`
- `/root/compliance_segment_summary.json`

Requirements:
- use the segment-combiner skill to create the combined segments JSON
- in the summary JSON record `segment_count`, `total_duration_seconds`, `first_segment_start`, and `last_segment_end`
