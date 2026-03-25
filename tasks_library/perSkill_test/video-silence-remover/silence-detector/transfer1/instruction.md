Detect initial intro silence from the provided compliance energy trace.

Input:
- `/root/data/compliance_energies.json`

Save:
- `/root/compliance_silence.json`
- `/root/compliance_silence_summary.json`

Requirements:
- use `threshold_multiplier=2.0`, `initial_window=5`, and `smoothing_window=4`
- save the silence detector output JSON
- in the summary JSON record `detected_silence_end`, `baseline_energy`, `threshold`, and `has_initial_silence`
