Use `/root/data/batch_manifest.json` to process three clip pairs and create `/root/transfer2_batch_summary.json`.

Expected structure:

```json
{
  "batch_id": "string",
  "reports": [
    {
      "clip_id": "string",
      "report": {
        "original_duration_seconds": 0,
        "compressed_duration_seconds": 0,
        "removed_duration_seconds": 0,
        "compression_percentage": 0,
        "segments_removed": []
      }
    }
  ],
  "portfolio": {
    "total_original_seconds": 0,
    "total_compressed_seconds": 0,
    "total_removed_seconds": 0,
    "mean_compression_percentage": 0
  }
}
```

Rules:

1. Preserve clip order from `batch_manifest.json`.
2. For jobs with a `segments` path, `segments_removed` must match that file's `segments` array.
3. For jobs without a `segments` path, `segments_removed` must be an empty list.
4. Portfolio fields must be computed from the per-clip reports.
