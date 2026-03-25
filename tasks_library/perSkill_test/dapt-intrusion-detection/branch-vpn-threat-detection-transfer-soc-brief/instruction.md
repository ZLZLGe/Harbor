You are given `/root/branch_vpn_hourly_features.csv`, which contains hourly VPN gateway feature summaries for several branch sites. Produce `/root/branch_soc_report.md`.

Each CSV row contains:
- `site_code`
- `region`
- `hour_utc`
- `port_entropy`
- `syn_only_ratio`
- `unique_destination_ports`
- `packets_per_minute_avg`
- `packets_per_minute_max`
- `iat_cv`

Evaluate threat flags for every hourly row using these exact rules:

Port scan:
- `port_scan` is `true` only when all three are strictly true:
  - `port_entropy > 6.0`
  - `syn_only_ratio > 0.7`
  - `unique_destination_ports > 100`

DoS pattern:
- `dos_pattern` is `true` only when `packets_per_minute_max / packets_per_minute_avg > 20`
- If `packets_per_minute_avg` is `0`, treat `dos_pattern` as `false`

Beaconing:
- `beaconing` is `true` only when `iat_cv < 0.5`

Site-level escalation rules:
- A site requires escalation when any of the three threat flags is `true` in at least one hourly row for that site.
- A site's triggered threats are the union of all hourly threat flags seen for that site.
- Use this exact threat order everywhere in the report: `port_scan`, `dos_pattern`, `beaconing`.

Evidence selection rules:
- For `port_scan`, choose the matching row with the largest `port_entropy`; if tied, choose the earlier `hour_utc`
- For `dos_pattern`, choose the matching row with the largest `packets_per_minute_max / packets_per_minute_avg`; if tied, choose the earlier `hour_utc`
- For `beaconing`, choose the matching row with the smallest `iat_cv`; if tied, choose the earlier `hour_utc`
- For `dos_pattern` evidence, round the ratio to exactly 2 decimal places in the report
- For all other numeric values shown in evidence lines, preserve the source value text from the chosen CSV row

Output requirements:
- Write a Markdown document with exactly these top-level sections in this order:
  - `# Branch VPN SOC Brief`
  - `## Global Summary`
  - `## Escalated Sites`
- Under `## Global Summary`, write exactly these five bullet lines:
  - `- Total sites analyzed: <integer>`
  - `- Sites requiring escalation: <integer>`
  - `- Sites with port_scan evidence: <integer>`
  - `- Sites with dos_pattern evidence: <integer>`
  - `- Sites with beaconing evidence: <integer>`
- Under `## Escalated Sites`, include only escalated sites, sorted by `site_code` ascending
- For each escalated site, create a heading in this exact format:
  - `### <site_code> (<region>)`
- Immediately below each site heading, write:
  - One bullet in this exact format:
    - `- Triggered threats: <comma-separated threat names in the required order>`
  - One evidence bullet for each triggered threat, in the same threat order, using these exact formats:
    - `- port_scan evidence: <hour_utc> | port_entropy=<value> (> 6.0), syn_only_ratio=<value> (> 0.7), unique_destination_ports=<value> (> 100)`
    - `- dos_pattern evidence: <hour_utc> | packets_per_minute_max/avg=<ratio> using <max>/<avg> (> 20)`
    - `- beaconing evidence: <hour_utc> | iat_cv=<value> (< 0.5)`
- If no sites require escalation, write exactly `No sites require escalation.` on the line after `## Escalated Sites`
