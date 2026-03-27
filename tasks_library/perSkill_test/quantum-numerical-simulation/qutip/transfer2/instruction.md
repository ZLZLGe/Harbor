You are given three two-qubit decoherence cases in `entanglement_cases.json`.

For each case:

1. Build the specified initial state.
2. Evolve the open two-qubit system across the provided time grid.
3. Track the concurrence and subsystem entropy through time.
4. Summarize the requested survival metrics in `/root/transfer2_entanglement_summary.json`.

Do not modify files under `environment/`.

Write `/root/transfer2_entanglement_summary.json` with exactly this structure:

```json
{
  "time_grid": {
    "start": 0.0,
    "stop": 4.0,
    "points": 121
  },
  "cases": [
    {
      "case_id": "case-name",
      "initial_concurrence": 0.0,
      "final_concurrence": 0.0,
      "min_concurrence": 0.0,
      "half_life_time": 0.0,
      "max_entropy_qubit_a": 0.0,
      "mean_total_excitation": 0.0
    }
  ],
  "ranking_by_final_concurrence": ["case-name"]
}
```

Requirements:

- Preserve the input case order in the `cases` array.
- Round every numeric value to 6 decimal places.
- `half_life_time` is the earliest grid time where concurrence is at or below half of its initial value.
- `max_entropy_qubit_a` is the largest von Neumann entropy reached by qubit A over the trajectory.
- `mean_total_excitation` is the average over time of the expectation value of the total excitation operator.
- `ranking_by_final_concurrence` must sort case ids by descending `final_concurrence`, breaking ties by descending `max_entropy_qubit_a`, then `case_id`.

No other output file is required.
