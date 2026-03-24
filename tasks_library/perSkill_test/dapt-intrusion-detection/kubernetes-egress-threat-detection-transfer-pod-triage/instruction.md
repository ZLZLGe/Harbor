You are given per-pod egress summaries from a Kubernetes cluster in `/root/pod_egress_metrics.json`.

Create `/root/pod_egress_findings.json` with this structure:

```json
{
  "cluster": "<copy from input>",
  "priority_order": ["port_scan", "dos_pattern", "beaconing", "benign"],
  "queue": [
    {
      "namespace": "<pod namespace>",
      "pod": "<pod name>",
      "owner": "<owner reference>",
      "labels": ["<one or more labels in priority order>"],
      "highest_priority_reason": "<first label>"
    }
  ],
  "summary": {
    "total_pods": 0,
    "malicious_pods": 0,
    "benign_pods": 0,
    "highest_priority_counts": {
      "port_scan": 0,
      "dos_pattern": 0,
      "beaconing": 0,
      "benign": 0
    }
  }
}
```

Rules:
- Use the provided metrics to decide whether each pod shows `port_scan`, `dos_pattern`, `beaconing`, or `benign` behavior.
- If a pod matches multiple malicious behaviors, include every matching malicious label in `labels` using the fixed priority order above.
- If a pod matches none of the malicious behaviors, set `labels` to `["benign"]`.
- `highest_priority_reason` must be the first entry in `labels`.
- Sort `queue` by the same priority order, then by `namespace`, then by `pod`.
- Do not modify `/root/pod_egress_metrics.json`.

Field meanings in each pod summary:
- `tcp_packet_count`: total TCP packets used for the per-pod scan summary
- `port_entropy`, `syn_only_ratio`, `unique_dst_ports`: port-spread and handshake behavior
- `packets_per_minute_avg`, `packets_per_minute_max`: average and peak egress rate
- `iat_cv`: coefficient of variation of packet inter-arrival times
