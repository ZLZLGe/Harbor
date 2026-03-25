Map QA quiet spans from the provided energy trace.

Input:
- `/root/data/qa_energies.json`

Save:
- `/root/qa_pauses.json`
- `/root/qa_pause_summary.json`

Requirements:
- detect pauses starting at second 0
- use `threshold_ratio=0.55`, `min_duration=3`, and `window_size=5`
- save the pause segments using the pause-detector skill output format
- in the summary JSON record `pause_count`, `total_pause_duration`, `longest_pause_start`, `longest_pause_duration`, and `analysis_start_time`
