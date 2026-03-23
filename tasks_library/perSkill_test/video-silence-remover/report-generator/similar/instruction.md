You are given one original lecture clip, one already-trimmed clip, and a JSON list of removed segments:

- `/root/data/source_session.mp4`
- `/root/data/trimmed_session.mp4`
- `/root/data/segments_removed.json`

Create `/root/similar_compression_report.json` with this schema:

```json
{
  "original_duration_seconds": 0,
  "compressed_duration_seconds": 0,
  "removed_duration_seconds": 0,
  "compression_percentage": 0,
  "segments_removed": []
}
```

Requirements:

1. Duration values must be computed from the media files.
2. `segments_removed` must match the segment list provided in `/root/data/segments_removed.json`.
3. Keep all numeric fields as JSON numbers.
4. Keep output strictly valid JSON.
