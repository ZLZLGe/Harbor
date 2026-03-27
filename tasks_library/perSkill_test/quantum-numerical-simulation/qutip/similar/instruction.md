You are given four dissipative cavity-qubit cases in `steady_state_cases.json`.

For each case:

1. Build the driven cavity-qubit Hamiltonian and collapse operators from the provided parameters.
2. Solve the steady state of the open system.
3. Trace out the qubit and evaluate the cavity Wigner function on the supplied square grid.
4. Summarize the required metrics in `/root/similar_phase_space_report.json`.

Do not modify files under `environment/`.

Write `/root/similar_phase_space_report.json` with exactly this structure:

```json
{
  "grid": {
    "min": -3.0,
    "max": 3.0,
    "points": 41
  },
  "cases": [
    {
      "case_id": "case-name",
      "mean_photon": 0.0,
      "qubit_excitation": 0.0,
      "wigner_center": 0.0,
      "wigner_min": 0.0,
      "wigner_max": 0.0,
      "normalization": 0.0,
      "centerline_signature": [0.0, 0.0, 0.0, 0.0, 0.0]
    }
  ],
  "ranking_by_mean_photon": ["case-name"]
}
```

Requirements:

- Keep the `grid` block exactly equal to the grid specification from `steady_state_cases.json`.
- Preserve the case order from the input file in the `cases` array.
- `centerline_signature` must contain exactly 5 numbers sampled from the Wigner function center row.
- Round every numeric value in the output to 6 decimal places.
- `ranking_by_mean_photon` must list all case ids sorted by descending `mean_photon`. Break ties by `case_id`.

No other output file is required.
