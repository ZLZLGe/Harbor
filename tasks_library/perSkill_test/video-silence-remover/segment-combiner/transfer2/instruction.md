Merge briefing cuts into a single ordered removal list.

Inputs:
- `/root/data/lead_in.json`
- `/root/data/gaps.json`

Save:
- `/root/briefing_all_segments.json`
- `/root/briefing_segment_summary.json`

Requirements:
- use the segment-combiner skill to create the combined segments JSON
- in the summary JSON record `segment_count`, `total_duration_seconds`, `first_segment_start`, and `last_segment_end`
