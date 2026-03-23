Two policy teams prepared timeline intervals:

1. `/root/schedule_segments.json`
2. `/root/compliance_segments.json`

Produce `/root/transfer2_overlap_alerts.json` with this format:

```json
{
  "total_segments": 0,
  "total_duration_seconds": 0,
  "has_overlaps": false,
  "overlap_alerts": [
    {
      "first_segment": {"start": 0, "end": 0, "duration": 0},
      "second_segment": {"start": 0, "end": 0, "duration": 0},
      "overlap": {"start": 0, "end": 0, "duration": 0}
    }
  ],
  "non_overlapping_segments": [
    {"start": 0, "end": 0, "duration": 0}
  ]
}
```

Rules:

1. First create one sorted combined segment timeline from both input files.
2. `overlap_alerts` must include every adjacent overlap in the sorted timeline.
3. `non_overlapping_segments` must include only segments that do not overlap with any neighbor.
4. All durations must satisfy `duration = end - start`.
