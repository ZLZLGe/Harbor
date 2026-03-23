Create `/root/transfer1_energy_alerts.json` from:

- `/root/data/broadcast_clip.wav`

Output format:

```json
{
  "clip_id": "broadcast-17",
  "window_seconds": 0.5,
  "energies": [20, 60, 140, 300, 300, 140, 60, 20],
  "peak_windows": [3, 4],
  "alert_windows": [2, 3, 4, 5],
  "mean_energy": 130
}
```

Rules:

1. Use 0.5-second windows.
2. `peak_windows` are indices equal to the global max energy.
3. `alert_windows` are indices where energy is `>= 140`.
4. `mean_energy` is the arithmetic mean of all window energies.
