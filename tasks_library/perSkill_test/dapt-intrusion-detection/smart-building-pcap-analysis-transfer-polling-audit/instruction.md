You are given `/root/smart_building_devices.pcap`, a packet capture from a smart-building controls segment. Facilities engineering wants a capture-level audit plus a short list of flows that look like periodic polling or one-way beaconing.

Analyze the PCAP and write `/root/smart_building_polling_audit.yaml` with exactly this structure:

```yaml
protocol_distribution:
  total_packets: 0
  ip_total: 0
  tcp: 0
  udp: 0
  icmp: 0
  arp: 0
global_iat:
  capture_duration_seconds: 0.0
  mean_seconds: 0.0
  variance_seconds: 0.0
  cv: 0.0
device_roles:
  num_producers: 0
  num_consumers: 0
flow_summary:
  unique_flows: 0
  tcp_flows: 0
  udp_flows: 0
  bidirectional_flows: 0
  bidirectional_flow_ratio: 0.0
polling_audit:
  periodic_polling_flow_count: 0
  beaconing_flow_count: 0
  polling_flows: []
  beaconing_flows: []
  obvious_periodic_polling: false
  obvious_beaconing: false
  final_assessment: no_obvious_periodic_activity
```

Definitions:

- Protocol distribution:
  - `total_packets`: all packets in the capture
  - `ip_total`: packets that contain an IPv4 layer
  - `tcp`, `udp`, `icmp`, `arp`: packet counts by protocol
- `capture_duration_seconds`: `last_timestamp - first_timestamp`, rounded to 2 decimals
- Sort all packet timestamps and compute inter-arrival times between consecutive packets:
  - `mean_seconds`: mean inter-arrival time, rounded to 6 decimals
  - `variance_seconds`: population variance of inter-arrival times, rounded to 6 decimals
  - `cv`: standard deviation divided by mean, rounded to 4 decimals. If the mean is zero, use `0.0`
- Producer / consumer counts use IPv4 packets only:
  - For each IP, `bytes_sent` is the sum of packet lengths where it is the source
  - `bytes_recv` is the sum of packet lengths where it is the destination
  - `PCR = (bytes_sent - bytes_recv) / (bytes_sent + bytes_recv)`
  - `num_producers`: IPs with `PCR > 0.2`
  - `num_consumers`: IPs with `PCR < -0.2`
- Flow key = `(src_ip, dst_ip, src_port, dst_port, protocol)` for TCP and UDP packets only
  - `unique_flows`: number of distinct flow keys
  - `tcp_flows` and `udp_flows`: distinct keys for that protocol
  - `bidirectional_flows`: count each TCP/UDP flow pair once when both directions exist
  - `bidirectional_flow_ratio = bidirectional_flows / unique_flows`, rounded to 4 decimals. If `unique_flows` is zero, use `0.0`
- `polling_audit` is based on per-flow timing:
  - Group packet timestamps by TCP/UDP flow key.
  - Ignore any flow with fewer than 5 packets.
  - For each remaining flow, sort that flow's timestamps and compute:
    - `packet_count`: number of packets in the flow
    - `mean_interval_seconds`: arithmetic mean of that flow's inter-arrival times, rounded to 2 decimals
    - `std_interval_seconds`: population standard deviation of that flow's inter-arrival times. Use this only for classification; do not write it to the YAML.
  - Render each flow as `src_ip:src_port->dst_ip:dst_port/proto` where `proto` is lowercase.
  - A flow belongs in `polling_flows` if all of the following hold:
    - the reverse flow key `(dst_ip, src_ip, dst_port, src_port, protocol)` exists
    - destination port is either `47808` or `20000`
    - `mean_interval_seconds` before rounding is between `8` and `20` seconds inclusive
    - `std_interval_seconds <= 0.2`
  - A flow belongs in `beaconing_flows` if all of the following hold:
    - the reverse flow key does not exist
    - `mean_interval_seconds` before rounding is between `15` and `90` seconds inclusive
    - `std_interval_seconds <= 0.2`
  - Each list entry must be a mapping with exactly these keys in this order:
    - `flow`
    - `packet_count`
    - `mean_interval_seconds`
  - Sort both `polling_flows` and `beaconing_flows` lexicographically by the rendered `flow` string.
  - `periodic_polling_flow_count` and `beaconing_flow_count` are the lengths of those lists.
  - `obvious_periodic_polling` is `true` if `periodic_polling_flow_count >= 2`, otherwise `false`.
  - `obvious_beaconing` is `true` if `beaconing_flow_count >= 1`, otherwise `false`.
  - `final_assessment` must be one of:
    - `mixed_periodic_activity` if both booleans are `true`
    - `building_polling_present` if only `obvious_periodic_polling` is `true`
    - `beaconing_present` if only `obvious_beaconing` is `true`
    - `no_obvious_periodic_activity` otherwise

A preinstalled Python helper module named `pcap_utils` is available for packet loading and common protocol, flow, timing, graph, and producer/consumer calculations. You may use it instead of reimplementing packet parsing.

Only write `/root/smart_building_polling_audit.yaml`.
