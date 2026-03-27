You are given three candidate pulse schedules in `gate_cases.json` for a detuned single qubit.

For each candidate:

1. Apply every segment in order using the provided drift and control amplitudes.
2. Compare the resulting transformation against the target `Rx(pi/2)` gate on the provided probe states.
3. Compute the requested fidelity metrics and rank the candidates.

Do not modify files under `environment/`.

Write `/root/transfer3_gate_audit.json` with exactly this structure:

```json
{
  "target_gate": "rx_pi_over_2",
  "best_candidate": "case-name",
  "candidates": [
    {
      "case_id": "case-name",
      "average_fidelity": 0.0,
      "max_infidelity": 0.0,
      "total_duration": 0.0,
      "probe_fidelities": {
        "0": 0.0,
        "1": 0.0,
        "+": 0.0,
        "-": 0.0,
        "+i": 0.0,
        "-i": 0.0
      }
    }
  ],
  "ranking": ["case-name"]
}
```

Requirements:

- Preserve the input case order in the `candidates` array.
- Round every numeric value to 6 decimal places.
- `average_fidelity` is the arithmetic mean of the six probe-state fidelities.
- `max_infidelity` is `1 - min(probe_fidelity)` for that candidate.
- `total_duration` is the sum of all segment durations.
- `ranking` must sort candidate ids by descending `average_fidelity`, then ascending `max_infidelity`, then ascending `total_duration`, then `case_id`.
- `best_candidate` must be the first item in `ranking`.

No other output file is required.
