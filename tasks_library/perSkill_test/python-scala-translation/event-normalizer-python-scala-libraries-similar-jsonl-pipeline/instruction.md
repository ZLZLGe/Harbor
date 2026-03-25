# JSONL Event Normalization

`/root/event_normalizer.py` is the reference Python module. Translate it into a Scala 2.13 implementation and write the result to `/root/EventNormalizer.scala`.

Your Scala file must expose `object EventNormalizer` in the default package with:

- `run(inputPath: java.nio.file.Path, outputPath: java.nio.file.Path): Unit`
- `main(args: Array[String]): Unit`

`main` must read `/root/challenge/input/events.jsonl` and write `/root/challenge/output/daily_report.json`.

The Scala program must preserve the Python module's behavior:

- Read non-empty JSONL lines from the input file.
- Normalize each event into an object with exactly these fields:
  - `id`
  - `occurred_at`
  - `event_type`
  - `actor`
  - `metadata`
- `id` comes from `event_id`.
- `occurred_at` comes from `occurred_at` or `timestamp`, must be converted to UTC, and must be formatted as `YYYY-MM-DDTHH:MM:SSZ`.
- The accepted timestamp formats are:
  - `%Y-%m-%dT%H:%M:%SZ`
  - `%Y-%m-%d %H:%M:%SZ`
  - `%Y/%m/%d %H:%M:%S %z`
  - `%Y-%m-%d %H:%M:%S%z`
  - `%d-%m-%Y %H:%M:%S` and this format should be treated as UTC
- `event_type` comes from `event_name` or `kind`.
- Event type normalization rules:
  - trim, lowercase, replace every run of non-alphanumeric characters with `_`, and strip leading or trailing `_`
  - then apply these aliases:
    - `login`, `login_success`, `signin`, `sign_in` -> `user_login`
    - `checkout_complete`, `order_placed`, `purchase` -> `order_completed`
    - `password_reset` -> `password_reset`
    - `session_timeout` -> `session_timeout`
- `actor` comes from `user` or `actor`, must be lowercased, trimmed, and have internal whitespace collapsed to a single space.
- `metadata` comes from the `details` string. Extract every `key=value` pair separated by `;`, lowercase the key, trim the value, and return an object. If `details` is missing, use an empty object.
- After normalization, sort events by `occurred_at` and then `id`.
- Write a report JSON object with exactly these top-level fields:
  - `total_events`
  - `by_type`
  - `actors`
  - `normalized_events`
- `total_events` is the number of normalized events.
- `by_type` is a JSON object of event type counts.
- `actors` is the sorted list of unique normalized actor values.
- `normalized_events` is the sorted normalized event list.

Use Scala idioms rather than a line-by-line rewrite, but keep the same observable results.
