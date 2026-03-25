Produce an RMS energy scan for the provided briefing audio block.

Input:
- `/root/data/briefing_block.wav`

Save:
- `/root/briefing_energy.json`
- `/root/briefing_energy_summary.json`

Requirements:
- calculate RMS energy with 2.0-second windows
- save the raw energy profile using the energy-calculator skill output format
- in the summary JSON record `window_count`, `loudest_window_index`, `quietest_window_index`, `active_window_count`, `activity_threshold`, and `mean_energy`
- treat a window as active when its RMS energy is greater than or equal to 4200.0
