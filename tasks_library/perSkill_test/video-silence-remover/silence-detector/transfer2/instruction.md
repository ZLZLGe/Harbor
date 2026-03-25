Detect initial lead-in silence from the provided briefing energy trace.

Input:
- `/root/data/briefing_energies.json`

Save:
- `/root/briefing_silence.json`
- `/root/briefing_silence_summary.json`

Requirements:
- use `threshold_multiplier=1.6`, `initial_window=3`, and `smoothing_window=2`
- save the silence detector output JSON
- in the summary JSON record `detected_silence_end`, `baseline_energy`, `threshold`, and `has_initial_silence`
