Remove lecture opening and pause spans from the provided AV clip.

Inputs:
- `/root/data/input.mp4`
- `/root/data/remove_segments.json`

Save:
- `/root/lecture_trimmed.mp4`
- `/root/lecture_trim_summary.json`

Requirements:
- use the video-processor skill to create the trimmed MP4
- also produce a summary JSON with `output_duration`, `removed_duration`, `segments_removed`, and `segments_kept`
