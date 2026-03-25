You are given `/root/capture_feature_matrix.json`, which contains precomputed summary features for several network captures. Produce `/root/capture_verdicts.json`.

Each input record has:
- `capture_id`
- `port_entropy`
- `syn_only_ratio`
- `unique_ports`
- `packets_per_minute_avg`
- `packets_per_minute_max`
- `iat_cv`

For every capture, write one JSON object with these fields:
- `capture_id`
- `has_port_scan`
- `has_dos_pattern`
- `has_beaconing`
- `is_traffic_benign`
- `dominant_risk`

Use these exact rules:

Port scan:
- `has_port_scan` is `true` only when all three are strictly true:
  - `port_entropy > 6.0`
  - `syn_only_ratio > 0.7`
  - `unique_ports > 100`

DoS pattern:
- `has_dos_pattern` is `true` only when `packets_per_minute_max / packets_per_minute_avg > 20`
- If `packets_per_minute_avg` is `0`, treat `has_dos_pattern` as `false`

Beaconing:
- `has_beaconing` is `true` only when `iat_cv < 0.5`

Benign:
- `is_traffic_benign` is `true` only when all three threat flags are `false`

`dominant_risk`:
- Use `"benign"` when no threat flags are true
- Use `"port_scan"`, `"dos_pattern"`, or `"beaconing"` when exactly one corresponding flag is true
- Use `"multi_threat"` when two or three threat flags are true

Output requirements:
- Write `/root/capture_verdicts.json` as a JSON array
- Preserve the same record order as the input file
- Use JSON booleans, not string booleans
