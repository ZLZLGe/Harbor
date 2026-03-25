Merge QA trim segments into a single ordered removal list.

Inputs:
- `/root/data/setup.json`
- `/root/data/quiet_spans.json`
- `/root/data/wrap.json`

Save:
- `/root/qa_all_segments.json`
- `/root/qa_segment_summary.json`

Requirements:
- use the segment-combiner skill to create the combined segments JSON
- in the summary JSON record `segment_count`, `total_duration_seconds`, `first_segment_start`, and `last_segment_end`
