Create `/root/transfer1_governance_report.json` using these inputs:

- `/root/data/original_briefing.mp4`
- `/root/data/trimmed_briefing.mp4`
- `/root/data/governance_policy.json`

Output contract:

```json
{
  "report_id": "string",
  "source_asset": "string",
  "compression_report": {
    "original_duration_seconds": 0,
    "compressed_duration_seconds": 0,
    "removed_duration_seconds": 0,
    "compression_percentage": 0,
    "segments_removed": []
  },
  "quality_gate": {
    "minimum_removed_seconds": 0,
    "passed": true
  }
}
```

Rules:

1. Set `report_id`, `source_asset`, and `minimum_removed_seconds` from `/root/data/governance_policy.json`.
2. Compute durations from the two media files.
3. Do not invent removed segments: `segments_removed` must be an empty list.
4. `passed` is true iff `removed_duration_seconds >= minimum_removed_seconds`.
