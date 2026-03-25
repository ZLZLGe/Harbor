You are given `/root/pod_egress_profiles.jsonl`, a JSONL file with one Kubernetes Pod egress profile per line. Produce `/root/pod_isolation_plan.yaml`.

Each input object contains:
- `namespace`
- `pod_name`
- `port_entropy`
- `syn_only_ratio`
- `unique_destination_ports`
- `packets_per_minute_avg`
- `packets_per_minute_max`
- `iat_cv`

Evaluate these threat flags for every Pod using the exact rules below:

Port scan:
- `has_port_scan` is `true` only when all three are strictly true:
  - `port_entropy > 6.0`
  - `syn_only_ratio > 0.7`
  - `unique_destination_ports > 100`

DoS pattern:
- `has_dos_pattern` is `true` only when `packets_per_minute_max / packets_per_minute_avg > 20`
- If `packets_per_minute_avg` is `0`, treat `has_dos_pattern` as `false`

Beaconing:
- `has_beaconing` is `true` only when `iat_cv < 0.5`

Map the active threat flags to `action` with these exact rules:
- `isolate` when `has_port_scan` is `true`
- `isolate` when both `has_dos_pattern` and `has_beaconing` are `true`
- `rate_limit` when only `has_dos_pattern` is `true`
- `observe` when only `has_beaconing` is `true`
- `allow` when none of the three threat flags are `true`

Set `immediate_isolation` to:
- `true` when `action` is `isolate`
- `false` otherwise

Set `trigger_reasons` to:
- A YAML list of the active flag names
- Use this exact order when multiple flags are active: `port_scan`, `dos_pattern`, `beaconing`
- Use an empty list when no flags are active

Output requirements:
- Write a YAML mapping with exactly these top-level keys:
  - `summary`
  - `pods`
- `summary` must contain:
  - `total_pods`
  - `immediate_isolation_pods`
  - `action_counts`
- `action_counts` must contain integer counts for:
  - `allow`
  - `observe`
  - `rate_limit`
  - `isolate`
- `pods` must be a YAML list in the same order as the input lines
- Every item in `pods` must contain exactly these keys:
  - `namespace`
  - `pod_name`
  - `action`
  - `immediate_isolation`
  - `trigger_reasons`
- Use YAML booleans, not string booleans
