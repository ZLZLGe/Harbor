Detect the initial lecture silence span from the provided energy trace.

Input:
- `/root/data/lecture_energies.json`

Save:
- `/root/lecture_silence.json`
- `/root/lecture_silence_summary.json`

Requirements:
- use `threshold_multiplier=1.8`, `initial_window=4`, and `smoothing_window=3`
- save the silence detector output JSON
- in the summary JSON record `detected_silence_end`, `baseline_energy`, `threshold`, and `has_initial_silence`
