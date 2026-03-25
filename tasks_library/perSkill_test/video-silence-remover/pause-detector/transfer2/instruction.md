Identify briefing gaps from the provided energy trace after the preamble.

Input:
- `/root/data/briefing_energies.json`

Save:
- `/root/briefing_pauses.json`
- `/root/briefing_pause_summary.json`

Requirements:
- detect pauses starting at second 3
- use `threshold_ratio=0.5`, `min_duration=2`, and `window_size=5`
- save the pause segments using the pause-detector skill output format
- in the summary JSON record `pause_count`, `total_pause_duration`, `longest_pause_start`, `longest_pause_duration`, and `analysis_start_time`
