You are covering a campus SOC shift. The packet capture has already been reduced into a workbook export under `/root/campus_feature_workbook/`:

- `traffic_overview.csv`: capture-level metrics for rate and timing analysis
- `scan_candidates.csv`: per-source TCP scanning features for candidate hosts

Apply the exact decision thresholds already provided in the environment for:
- port-scan detection
- DoS-pattern detection
- beaconing detection
- benign-versus-malicious final judgment

Do not invent alternate heuristics. Use the workbook values directly.

Write `/root/campus_verdict.json` with this exact shape:

```json
{
  "capture_id": "string",
  "verdict": "benign or malicious",
  "is_traffic_benign": true,
  "has_port_scan": false,
  "has_dos_pattern": false,
  "has_beaconing": false,
  "supporting_metrics": {
    "port_scan_source": "string or null",
    "port_scan_unique_ports": 0,
    "port_scan_dst_port_entropy": 0.0,
    "port_scan_syn_only_ratio": 0.0,
    "packets_per_minute_avg": 0.0,
    "packets_per_minute_max": 0,
    "dos_ratio": 0.0,
    "iat_cv": 0.0
  }
}
```

Rules:
- `port_scan_source` must be the source IP that actually satisfies the exact port-scan rule, or `null` if none do.
- `dos_ratio` must be `packets_per_minute_max / packets_per_minute_avg`.
- `verdict` must be `"benign"` only when the traffic is benign; otherwise use `"malicious"`.
- The JSON must be valid and contain no extra top-level keys.
