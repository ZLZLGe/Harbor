Find low-energy hold spans in the provided compliance call energy trace.

Input:
- `/root/data/call_energies.json`

Save:
- `/root/call_pauses.json`
- `/root/call_pause_summary.json`

Requirements:
- detect pauses starting at second 1
- use `threshold_ratio=0.6`, `min_duration=2`, and `window_size=5`
- save the pause segments using the pause-detector skill output format
- in the summary JSON record `pause_count`, `total_pause_duration`, `longest_pause_start`, `longest_pause_duration`, and `analysis_start_time`
