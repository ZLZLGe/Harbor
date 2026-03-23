Create `/root/similar_energy_profile.json` using this input:

- `/root/data/lesson_track.wav`

Required JSON format:

```json
{
  "track_id": "lesson-track-a",
  "window_seconds": 1,
  "energies": [0, 120, 240, 0, 360],
  "stats": {
    "min": 0,
    "max": 360,
    "mean": 144,
    "std": 139.942845
  },
  "quiet_seconds": [0, 3],
  "loudest_second": 4
}
```

Rules:

1. Use 1-second windows.
2. `quiet_seconds` must include indices where energy is `<= 50`.
3. `loudest_second` is the first index of the maximum energy.
4. Preserve numeric precision from calculation results (do not round to integers unless naturally integral).
