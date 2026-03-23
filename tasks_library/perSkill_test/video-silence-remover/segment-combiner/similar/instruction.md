Two timeline files are provided:

1. `/root/intro_segments.json`
2. `/root/pause_segments.json`

Create `/root/similar_combined_segments.json` with this shape:

```json
{
  "segments": [
    {"start": 0, "end": 0, "duration": 0}
  ],
  "total_segments": 0,
  "total_duration_seconds": 0
}
```

Rules:

1. Include all segments from both input files.
2. Sort output segments by ascending `start`.
3. `total_segments` must equal the number of merged segments.
4. `total_duration_seconds` must equal the sum of segment `duration` values.
5. Keep numeric values as JSON numbers.
