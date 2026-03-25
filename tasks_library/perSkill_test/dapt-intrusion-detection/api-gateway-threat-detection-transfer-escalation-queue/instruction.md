You are given `/root/gateway_tenant_profiles.tsv`, a tab-separated table with one SaaS API gateway tenant profile per row. Produce `/root/gateway_escalations.csv`.

Each input row contains:
- `tenant_id`
- `plan_tier`
- `home_region`
- `dst_port_entropy`
- `syn_probe_ratio`
- `distinct_external_ports`
- `rpm_baseline`
- `rpm_peak`
- `checkin_iat_cv`

Evaluate threat flags for every tenant using these exact rules:

Port scan:
- `port_scan` is `true` only when all three are strictly true:
  - `dst_port_entropy > 6.0`
  - `syn_probe_ratio > 0.7`
  - `distinct_external_ports > 100`

DoS pattern:
- `dos_pattern` is `true` only when `rpm_peak / rpm_baseline > 20`
- If `rpm_baseline` is `0`, treat `dos_pattern` as `false`

Beaconing:
- `beaconing` is `true` only when `checkin_iat_cv < 0.5`

Build `threat_labels` from the active threat flags:
- Use this exact order when multiple threats are active: `port_scan`, `dos_pattern`, `beaconing`
- Join multiple active threats with `;`
- Use exactly `benign` when none of the three threat flags are active

Assign `priority` with these exact rules:
- `critical` when both `port_scan` and `dos_pattern` are `true`
- `high` when not `critical` and either:
  - `port_scan` is `true`, or
  - both `dos_pattern` and `beaconing` are `true`
- `medium` when neither `critical` nor `high` applies and at least one of `dos_pattern` or `beaconing` is `true`
- `low` when none of the three threat flags are `true`

Assign `dispatch_queue` with these exact rules:
- `tenant-abuse` when `port_scan` is `true`
- `traffic-surge` when `port_scan` is `false` and `dos_pattern` is `true`
- `signal-review` when only `beaconing` is `true`
- `baseline-monitoring` when no threat flags are `true`

Output requirements:
- Write a CSV file with exactly this header:
  - `tenant_id,threat_labels,priority,dispatch_queue`
- Write exactly one output row per input row
- Sort rows by `priority` using this order: `critical`, `high`, `medium`, `low`
- Break ties by `tenant_id` ascending
- Do not include any extra columns
