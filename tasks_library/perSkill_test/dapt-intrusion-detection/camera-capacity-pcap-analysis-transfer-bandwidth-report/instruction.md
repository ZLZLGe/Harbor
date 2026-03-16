You are given:

- `/root/packets.pcap`
- `/root/camera_stream_map.csv`

Write exactly one TSV file to `/root/camera_capacity_report.tsv`.

The mapping CSV contains one expected camera uplink stream per row with these fields:

- `stream_id`
- `camera_id`
- `camera_ip`
- `destination_ip`
- `protocol`
- `dst_port`
- `uplink_id`

Match packets to a mapped stream only when all of these fields match exactly:

- IPv4 source address = `camera_ip`
- IPv4 destination address = `destination_ip`
- transport protocol = `protocol` (`TCP` or `UDP`)
- destination port = `dst_port`

Ignore every packet that does not match a mapped stream exactly.

Use 60-second buckets relative to the timestamp of the first packet in the PCAP. For each mapped stream:

- `packet_count`: number of matched packets
- `total_bytes`: sum of the original packet lengths in bytes
- `active_minutes`: number of non-empty 60-second buckets for that stream
- `avg_kbps`: average kilobits per second across the stream's non-empty minute buckets
  - `avg_kbps = total_bytes * 8 / (active_minutes * 60 * 1000)`
- `peak_minute_index`: the bucket index with the largest byte count
- `peak_minute_kbps`: kilobits per second for that peak bucket
  - `peak_minute_kbps = peak_bucket_bytes * 8 / (60 * 1000)`
- `burst_ratio = peak_minute_kbps / avg_kbps`
- `anomalous_burst`: `true` if both of these are true, otherwise `false`
  - `burst_ratio >= 6`
  - `peak_minute_kbps >= 5`

Per-uplink summary:

- Aggregate matched bytes per minute across all streams that share the same `uplink_id`.
- `most_congested_uplink` is the uplink whose aggregated minute bucket has the highest `peak_minute_kbps`.
- Also report that uplink's `peak_minute_index` and `peak_minute_kbps`.
- `burst_stream_count` is the number of mapped streams whose `anomalous_burst` is `true`.
- `burst_stream_ids` is the comma-separated list of bursty `stream_id` values, sorted ascending. Use an empty string if none are bursty.

Tie-breaking:

- If a stream has multiple peak buckets with the same bytes, use the earliest `peak_minute_index`.
- If multiple uplinks have the same aggregated peak rate, choose the lexicographically smallest `uplink_id`; if that still ties on rate, use the earliest peak minute.

Output TSV schema:

```tsv
record_type	stream_id	camera_id	uplink_id	camera_ip	destination_ip	protocol	dst_port	packet_count	total_bytes	active_minutes	avg_kbps	peak_minute_index	peak_minute_kbps	burst_ratio	anomalous_burst	summary_metric	summary_value
```

Requirements:

- Write all mapped stream rows first, in the same order as `camera_stream_map.csv`, with `record_type=stream`.
- Then write exactly these six summary rows with `record_type=summary`, in this order:
  - `total_stream_count`
  - `most_congested_uplink`
  - `most_congested_peak_minute`
  - `most_congested_peak_kbps`
  - `burst_stream_count`
  - `burst_stream_ids`
- In summary rows, leave the stream-specific columns empty and fill only `summary_metric` and `summary_value`.
- Format `avg_kbps`, `peak_minute_kbps`, and `burst_ratio` with exactly three digits after the decimal point.
- Write booleans as lowercase `true` or `false`.
- Do not write any extra files.
