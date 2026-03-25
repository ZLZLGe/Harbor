Build an RMS energy profile for the provided lecture-aligned WAV track.

Input:
- `/root/data/lecture_track.wav`

Save:
- `/root/lecture_energy.json`
- `/root/lecture_energy_summary.json`

Requirements:
- calculate RMS energy with 1.0-second windows
- save the raw energy profile using the energy-calculator skill output format
- in the summary JSON record `window_count`, `loudest_window_index`, `quietest_window_index`, `active_window_count`, `activity_threshold`, and `mean_energy`
- treat a window as active when its RMS energy is greater than or equal to 3000.0
