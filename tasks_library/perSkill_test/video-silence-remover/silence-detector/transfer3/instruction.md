Detect initial setup silence from the provided QA energy trace.

Input:
- `/root/data/qa_energies.json`

Save:
- `/root/qa_silence.json`
- `/root/qa_silence_summary.json`

Requirements:
- use `threshold_multiplier=1.7`, `initial_window=4`, and `smoothing_window=5`
- save the silence detector output JSON
- in the summary JSON record `detected_silence_end`, `baseline_energy`, `threshold`, and `has_initial_silence`
