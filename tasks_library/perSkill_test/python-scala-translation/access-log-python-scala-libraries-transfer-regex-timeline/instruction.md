# Access Log Session Analysis

`/root/access_log_analyzer.py` is the reference Python program. Translate it into Scala 2.13 and write the result to `/root/AccessLogAnalyzer.scala`.

Your Scala file must expose `object AccessLogAnalyzer` in the default package with:

- `analyze(inputPath: java.nio.file.Path, sessionGapMinutes: Int): Seq[SessionSummary]`
- `run(inputPath: java.nio.file.Path, outputPath: java.nio.file.Path, sessionGapMinutes: Int): Unit`
- `main(args: Array[String]): Unit`

Your Scala file must also expose `final case class SessionSummary` with these fields:

- `sessionId: String`
- `clientId: String`
- `userId: String`
- `sessionStartUtc: String`
- `sessionEndUtc: String`
- `durationMinutes: Int`
- `requestCount: Int`
- `status2xx: Int`
- `status4xx: Int`
- `status5xx: Int`
- `totalBytes: Int`
- `paths: String`

`main` must read `/root/challenge/input/access.log`, use a session gap of `30` minutes, and write `/root/challenge/output/session_summary.csv`.

The Scala program must preserve the Python program's behavior:

- Read UTF-8 log lines from the input file.
- Ignore blank lines and lines whose trimmed form starts with `#`.
- Parse only log lines that match this shape:
  - `[timestamp] client=<client_id> user=<user_id> method=<HTTP_METHOD> path=<path> status=<three_digit_status> bytes=<non_negative_integer>`
- Accepted timestamp formats are:
  - `%d/%b/%Y:%H:%M:%S %z`
  - `%Y-%m-%dT%H:%M:%S%z`
- Convert every parsed timestamp to UTC and format it as `YYYY-MM-DDTHH:MM:SSZ`.
- Build sessions independently for each `(client_id, user_id)` pair.
- Within each `(client_id, user_id)` pair, sort requests by timestamp, then path, then status before sessionizing.
- Start a new session when the gap between consecutive requests is strictly greater than `sessionGapMinutes`.
- Session ids must use the exact pattern `<client_id>:<user_id>:sNN`, where `NN` is the 1-based session index within that `(client_id, user_id)` pair, zero-padded to two digits.
- For each session, produce one CSV row with exactly these columns in this order:
  - `session_id`
  - `client_id`
  - `user_id`
  - `session_start_utc`
  - `session_end_utc`
  - `duration_minutes`
  - `request_count`
  - `status_2xx`
  - `status_4xx`
  - `status_5xx`
  - `total_bytes`
  - `paths`
- `duration_minutes` is the whole-minute difference between the first and last request in the session.
- `request_count` is the number of requests in the session.
- `status_2xx`, `status_4xx`, and `status_5xx` are counts of statuses in those ranges.
- `total_bytes` is the sum of `bytes` across the session.
- `paths` is the lexicographically sorted unique path list joined by `|`.
- Sort the final CSV rows by `session_start_utc`, then `session_id`.

Use Scala idioms rather than a line-by-line rewrite, but keep the same observable results.
