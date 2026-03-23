Input files:

- `/root/qc_manifest.json` (batch entries and detection/QC policy)
- energy files referenced by the manifest

Produce `/root/silence_qc_flags.json` with this structure:

```json
{
  "records": [
    {"recording_id": "rec-a", "silence_seconds": 4, "qc_flag": "ok"}
  ],
  "summary": {
    "ok": 2,
    "review": 1,
    "reject": 1,
    "total": 4
  }
}
```

Rules:

1. Use detection parameters from `qc_manifest.json` exactly.
2. For each recording, compute `silence_seconds` from initial low-energy boundary detection.
3. Assign `qc_flag` by policy:
   - `ok` when `silence_seconds <= ok_max_seconds`
   - `review` when `ok_max_seconds < silence_seconds <= review_max_seconds`
   - `reject` when `silence_seconds > review_max_seconds`
4. Keep `records` in manifest order.
5. `summary` counts must exactly match `records`.
