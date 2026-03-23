Build `/root/transfer3_candidate_selection.json` from:

- `/root/data/master_source.mp4`
- `/root/data/candidate_manifest.json`

`candidate_manifest.json` provides a target compression window and candidate files.

Output schema:

```json
{
  "target_window": {
    "min_pct": 0,
    "max_pct": 0,
    "target_pct": 0
  },
  "candidates": [
    {
      "candidate_id": "string",
      "report": {
        "original_duration_seconds": 0,
        "compressed_duration_seconds": 0,
        "removed_duration_seconds": 0,
        "compression_percentage": 0,
        "segments_removed": []
      }
    }
  ],
  "selected_candidate": "string",
  "selected_report": {}
}
```

Selection rule:

1. Compute a report for every candidate in manifest order.
2. Keep only candidates with `compression_percentage` in `[min_pct, max_pct]`.
3. Select the remaining candidate with smallest absolute difference from `target_pct`.
4. If there is a tie, select the lexicographically smallest `candidate_id`.
