Create `/root/transfer3_energy_delta.json` from:

- `/root/data/line_a.wav`
- `/root/data/line_b.wav`

Output format:

```json
{
  "comparison_id": "line-a-vs-line-b",
  "window_seconds": 1,
  "baseline_mean": 123.333333,
  "candidate_mean": 101.666667,
  "reduction_ratio": 0.1756756757,
  "per_second_delta": [10, 20, 40, 30, 20, 10],
  "improved_seconds": [0, 1, 2, 3, 4, 5]
}
```

Rules:

1. Use 1-second windows for both files.
2. Treat `line_a.wav` as baseline and `line_b.wav` as candidate.
3. `per_second_delta[i] = baseline_energy[i] - candidate_energy[i]`.
4. `improved_seconds` are indices with strictly positive delta.
5. `reduction_ratio = (baseline_mean - candidate_mean) / baseline_mean`.
