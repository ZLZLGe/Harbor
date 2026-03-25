Generate a compression report for the provided lecture-style edit package.

Inputs:
- `/root/data/original.mp4`
- `/root/data/compressed.mp4`
- `/root/data/segments.json`

Save:
- `/root/lecture_report.json`
- `/root/lecture_report_brief.json`

Requirements:
- use the report-generator skill to create the main report JSON
- the brief JSON must record `segment_count`, `removed_duration_seconds`, `compression_percentage`, `longest_segment_duration`, and `segment_total_duration_seconds`
