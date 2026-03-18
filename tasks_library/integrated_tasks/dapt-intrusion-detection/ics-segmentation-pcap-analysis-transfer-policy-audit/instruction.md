You are given three files:

- `/root/packets.pcap`
- `/root/asset_inventory.csv`
- `/root/zone_policy.json`

Write exactly one JSON file to `/root/ot_policy_audit.json`.

Audit rules:

- Reconstruct communication edges from the PCAP at the granularity `(src_ip, dst_ip, protocol)`.
- Only audit IPv4 unicast packets where both endpoints appear in `asset_inventory.csv`.
- Ignore ARP, any non-IPv4 packet, any packet whose source or destination is `0.0.0.0` or `255.255.255.255`, and any multicast packet.
- Only keep `TCP`, `UDP`, and `ICMP`.
- For `dst_ports`, record the sorted unique destination ports observed on that directed edge. Use `[]` for `ICMP`.
- A graph edge is a policy violation when `src_zone != dst_zone` and there is no matching allow rule in `zone_policy.json` for the tuple `(src_zone, dst_zone, protocol)`.

Output JSON format:

```json
{
  "summary": {
    "audited_asset_count": 0,
    "audited_packet_count": 0,
    "directed_edge_count": 0,
    "allowed_edge_count": 0,
    "allowed_packet_count": 0,
    "cross_zone_edge_count": 0,
    "violating_edge_count": 0,
    "violating_packet_count": 0,
    "violating_direction_counts": {
      "zone_a->zone_b": 0
    },
    "violating_direction_packet_counts": {
      "zone_a->zone_b": 0
    }
  },
  "communication_graph": [
    {
      "src_ip": "x.x.x.x",
      "src_asset": "asset-name",
      "src_zone": "zone-name",
      "dst_ip": "y.y.y.y",
      "dst_asset": "asset-name",
      "dst_zone": "zone-name",
      "protocol": "TCP",
      "packet_count": 0,
      "dst_ports": [80, 443],
      "cross_zone": true,
      "direction": "zone-name->zone-name",
      "status": "allowed"
    }
  ],
  "violations": [
    {
      "src_ip": "x.x.x.x",
      "src_asset": "asset-name",
      "src_zone": "zone-name",
      "dst_ip": "y.y.y.y",
      "dst_asset": "asset-name",
      "dst_zone": "zone-name",
      "protocol": "TCP",
      "packet_count": 0,
      "dst_ports": [80, 443],
      "cross_zone": true,
      "direction": "zone-name->zone-name",
      "status": "violation",
      "reason": "no matching allow rule"
    }
  ]
}
```

Additional requirements:

- Sort both `communication_graph` and `violations` by `(src_ip, dst_ip, protocol)`.
- `violations` must be the exact subset of `communication_graph` entries whose `status` is `violation`, with the added `reason` field shown above.
- Do not write any extra files.
