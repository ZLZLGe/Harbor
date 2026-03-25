Prepare an RMS energy scan for the provided compliance call clip.

Input:
- `/root/data/call_preview.wav`

Save:
- `/root/call_energy.json`
- `/root/call_energy_summary.json`

Requirements:
- calculate RMS energy with 0.5-second windows
- save the raw energy profile using the energy-calculator skill output format
- in the summary JSON record `window_count`, `loudest_window_index`, `quietest_window_index`, `active_window_count`, `activity_threshold`, and `mean_energy`
- treat a window as active when its RMS energy is greater than or equal to 2400.0
