You are given `/root/branch_office_incident.pcap` and a metrics template at `/root/branch_incident_metrics.csv`.

Fill in only the `value` column of `/root/branch_incident_metrics.csv`. Leave comment rows whose `metric` starts with `#` unchanged.

Compute these metrics from the PCAP:

Protocol distribution
- `protocol_tcp`, `protocol_udp`, `protocol_icmp`, `protocol_arp`: packet counts by protocol
- `protocol_ip_total`: packets that contain an IPv4 layer

Rate buckets
- `duration_seconds`: `last_timestamp - first_timestamp`
- `packets_per_minute_avg`, `packets_per_minute_max`, `packets_per_minute_min`: count packets in 60-second buckets relative to the first packet timestamp, then take avg / max / min across non-empty buckets

Packet sizes
- `total_bytes`: sum of packet lengths in bytes
- `avg_packet_size`, `min_packet_size`, `max_packet_size`: statistics over packet lengths

Entropy (Shannon)
- `src_ip_entropy`, `dst_ip_entropy`: entropy of observed source / destination IPv4 addresses
- `src_port_entropy`, `dst_port_entropy`: entropy of observed TCP+UDP source / destination ports
- `unique_src_ports`, `unique_dst_ports`: number of distinct TCP+UDP source / destination ports

Communication graph
- Nodes are distinct IPv4 addresses seen as source or destination
- Edges are distinct directed `(src_ip, dst_ip)` pairs
- `num_nodes`, `num_edges`
- `network_density = num_edges / (num_nodes * (num_nodes - 1))`; use `0` if `num_nodes < 2`
- `max_outdegree`: max number of distinct destinations contacted by one source
- `max_indegree`: max number of distinct sources contacting one destination

Timing and host roles
- Sort packets by timestamp and compute inter-arrival times between consecutive packets
- `iat_mean`, `iat_variance`
- `iat_cv = std(iat) / mean(iat)`; use `0` if the mean is `0`
- For each IPv4 address, compute producer/consumer ratio `PCR = (sent_bytes - recv_bytes) / (sent_bytes + recv_bytes)` using IPv4 packet lengths
- `num_producers`: number of IPs with `PCR > 0.2`
- `num_consumers`: number of IPs with `PCR < -0.2`

Flows
- Flow key = `(src_ip, dst_ip, src_port, dst_port, protocol)` over TCP and UDP packets
- `unique_flows`, `tcp_flows`, `udp_flows`
- `bidirectional_flows`: number of flows whose reverse key `(dst_ip, src_ip, dst_port, src_port, protocol)` also exists

Incident judgement
- `has_port_scan` is `true` if any source IP has all three of:
  - more than 100 unique TCP destination ports
  - destination-port entropy greater than `6.0`
  - SYN-only ratio greater than `0.7`
  - ignore sources with fewer than 50 TCP packets
- `has_dos_pattern` is `true` if `packets_per_minute_max / packets_per_minute_avg > 20`
- `has_beaconing` is `true` if `iat_cv < 0.5`
- `is_traffic_benign` is `true` only if all three attack flags above are `false`

Write booleans as lowercase `true` or `false`.
