Input files:

- `/root/module_energies.json` (per-second energy timeline)
- `/root/trim_policy.json` (detection parameters and publish policy)

Produce `/root/intro_trim_plan.json` with this structure:

```json
{
  "detected_intro_end_seconds": 22,
  "publish_start_seconds": 24,
  "cut_segment": {
    "start": 0,
    "end": 24,
    "duration": 24
  },
  "policy_applied": {
    "safety_buffer_seconds": 2,
    "min_publish_start_second": 20,
    "max_publish_start_second": 30
  }
}
```

Rules:

1. Detect the initial low-energy boundary using the exact detection parameters from `/root/trim_policy.json`.
2. Compute `publish_start_seconds` as:
   `clamp(detected_intro_end_seconds + safety_buffer_seconds, min_publish_start_second, max_publish_start_second)`.
3. `cut_segment.start` must be `0`.
4. `cut_segment.end` must equal `publish_start_seconds`.
5. `cut_segment.duration` must equal `end - start`.
