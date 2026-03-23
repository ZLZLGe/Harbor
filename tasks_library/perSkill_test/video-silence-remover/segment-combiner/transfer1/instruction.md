Three reviewers produced candidate cut timelines:

1. `/root/reviewer_a_segments.json`
2. `/root/reviewer_b_segments.json`
3. `/root/reviewer_c_segments.json`

Produce these files:

1. `/root/transfer1_all_segments.json`
2. `/root/transfer1_review_manifest.json`

`/root/transfer1_review_manifest.json` must follow:

```json
{
  "segment_files_used": [
    "/root/reviewer_a_segments.json",
    "/root/reviewer_b_segments.json",
    "/root/reviewer_c_segments.json"
  ],
  "combined_segments_output": "/root/transfer1_all_segments.json",
  "total_segments": 0,
  "total_duration_seconds": 0,
  "max_single_segment_seconds": 0,
  "reviewer_stats": [
    {"reviewer": "reviewer_a", "segment_count": 0, "duration_seconds": 0}
  ]
}
```

Rules:

1. `transfer1_all_segments.json` must include all segments from all reviewers, sorted by `start`.
2. `reviewer_stats` must keep reviewer order: `reviewer_a`, `reviewer_b`, `reviewer_c`.
3. `total_segments` and `total_duration_seconds` must reflect the combined output.
4. `max_single_segment_seconds` is the maximum `duration` value in the combined segments.
