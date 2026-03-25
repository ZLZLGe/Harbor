# Transfer: Streaming Clickstream Session Rollup

In `/root/workspace/` there is a baseline script `session_rollup_baseline.py` and a fixture generator `clickstream_fixture.py`.

The baseline reads a session-sorted NDJSON clickstream and emits one CSV row per session, but it materializes far too much data in memory. You need to write a replacement at `/root/workspace/session_rollup_solution.py`.

Your script must support this command line interface:

```bash
python /root/workspace/session_rollup_solution.py \
  --input /path/to/clickstream.ndjson \
  --output /path/to/session_rollup.csv
```

Input format:

- The input file is NDJSON: each non-empty line is one JSON object.
- Every event includes at least these fields:
  - `session_id` (string)
  - `user_id` (string)
  - `event_time` (integer Unix timestamp in seconds)
  - `page` (string)
  - `event_type` (string)
- The file is already sorted by `(session_id, event_time)` ascending.
- All events in the same session belong to the same `user_id`.

Output contract:

1. Write a CSV file to `--output` with this exact header order:

```text
session_id,user_id,event_count,session_duration_seconds,entry_page,converted
```

2. Emit exactly one row per session, in the same session order as the input file.
3. Compute each column as follows:
   - `event_count`: total number of events in that session.
   - `session_duration_seconds`: `last_event_time - first_event_time`.
   - `entry_page`: the `page` value from the first event in the session.
   - `converted`: `1` if any event in the session has `event_type == "purchase"`, otherwise `0`.
4. The CSV must not contain extra columns.
5. Your results must match the baseline semantics on the provided sample input and on the verifier fixtures.
6. On the large verifier fixture, peak RSS must stay at or below `180 MB`.
7. You may use `/tmp` for temporary files if needed, but the only required deliverable is `/root/workspace/session_rollup_solution.py`.

Available assets:

- `/root/workspace/session_rollup_baseline.py`
- `/root/workspace/clickstream_fixture.py`
- `/root/workspace/sample_clickstream.ndjson`

The verifier will run your script on multiple clickstream fixtures and check both correctness and memory usage.
