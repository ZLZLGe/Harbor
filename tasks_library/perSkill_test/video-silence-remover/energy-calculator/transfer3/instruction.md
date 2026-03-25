Generate an RMS energy trace for the provided QA cue track.

Input:
- `/root/data/qa_cues.wav`

Save:
- `/root/qa_energy.json`
- `/root/qa_energy_summary.json`

Requirements:
- calculate RMS energy with 0.25-second windows
- save the raw energy profile using the energy-calculator skill output format
- in the summary JSON record `window_count`, `loudest_window_index`, `quietest_window_index`, `active_window_count`, `activity_threshold`, and `mean_energy`
- treat a window as active when its RMS energy is greater than or equal to 1500.0
