You are given a fragment manifest at `/root/data/segment_manifest.csv` and a directory of listed MiniSEED files at `/root/data/segments/`.

Each manifest row identifies one waveform batch file from a continuous volcano-monitoring archive. A listed MiniSEED file may contain one or more trace segments.

Your task is to inspect the archive and write a machine-readable waveform quality-control report to `/root/volcano_trace_qc.json`.

Build the report with exactly this top-level structure:

```json
{
  "archive_id": "volcano-monitoring-qc",
  "summary": { ... },
  "traces": [ ... ]
}
```

Rules:

1. Only use files listed in `/root/data/segment_manifest.csv`.
2. Load every listed MiniSEED file. Treat every trace in every file as one segment, and group all segments by full trace ID: `network.station.location.channel`.
3. Within each trace group, sort segments by:
   - `starttime` ascending
   - then `file_name` ascending for ties
   - then the segment's original position inside that file for any remaining ties
4. Treat each segment as the half-open interval `[starttime, endtime + delta)`, where `delta` is the trace sample interval.
5. For each adjacent segment pair in a sorted trace group:
   - `gap_seconds = next.starttime - (current.endtime + current.delta)` if that value is positive, otherwise `0`
   - `overlap_seconds = (current.endtime + current.delta) - next.starttime` if that value is positive, otherwise `0`
6. For each trace group, compute:
   - `trace_id`
   - `segment_count`
   - `segment_files`: file names in the sorted segment order, allowing repeated names when one file contributes multiple segments to the same trace
   - `start_time`: earliest segment `starttime`
   - `end_time`: latest segment exclusive end time, i.e. `endtime + delta`
   - `span_seconds = end_time - start_time`
   - `covered_seconds = span_seconds - total_gap_seconds`
   - `sample_rates_hz`: sorted unique sampling rates
   - `sample_rate_inconsistent`: `true` if more than one unique sampling rate appears
   - `gap_count`
   - `gap_durations_seconds`
   - `total_gap_seconds`
   - `overlap_count`
   - `overlap_durations_seconds`
   - `total_overlap_seconds`
7. The `summary` object must contain:
   - `trace_count`
   - `total_segment_count`
   - `archive_start`: earliest trace-group `start_time`
   - `archive_end`: latest trace-group `end_time`
   - `traces_with_gaps`
   - `traces_with_overlaps`
   - `traces_with_sample_rate_inconsistency`
   - `total_gap_seconds`
   - `total_overlap_seconds`
8. Sort `traces` by `trace_id` ascending.
9. Format every timestamp as ISO without timezone and with microseconds: `%Y-%m-%dT%H:%M:%S.%f`
10. Round every reported duration or sampling-rate number to 6 decimal places.

Only `/root/volcano_trace_qc.json` will be graded.
