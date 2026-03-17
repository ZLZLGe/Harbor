You are given three input files:

- `/root/packets.pcap`
- `/root/device_inventory.csv`
- `/root/approved_periodic_flows.csv`

Write exactly one Markdown report to `/root/iot_beacon_report.md`.

Treat this as an IoT beacon-hunting investigation. Use the following rules:

1. Only analyze IPv4 `TCP`, `UDP`, and `ICMP` packets whose source IP appears in `device_inventory.csv`.
2. Aggregate packets into directional flows using:
   - `(src_ip, dst_ip, protocol, dst_port)` for `TCP` and `UDP`
   - `(src_ip, dst_ip, ICMP, -)` for `ICMP`
3. For each aggregated flow, sort packet timestamps and compute:
   - `packet_count`
   - `first_seen_utc`
   - `last_seen_utc`
   - `mean_iat_seconds`
   - `iat_cv`
4. A flow is a periodic candidate only if:
   - `packet_count >= 6`
   - `mean_iat_seconds >= 600`
   - `iat_cv <= 0.8`
5. `mean_iat_seconds` must be rounded to 2 decimal places and `iat_cv` to 4 decimal places in the report.
6. `first_seen_utc` and `last_seen_utc` must use UTC format `YYYY-MM-DDTHH:MM:SSZ`.
7. Classify each periodic candidate flow as:
   - `approved_periodic` if the exact tuple `(src_ip, dst_ip, protocol, dst_port)` appears in `approved_periodic_flows.csv`
   - `suspected_beacon` otherwise
8. `highest_risk_device` is the inventoried device with the largest number of `suspected_beacon` flows. Break ties by lexicographically smaller `device_id`.
9. Sort both tables by `(device_id, dst_ip, protocol, dst_port)`.
10. Do not write any extra files.

The report must use exactly this section order and these table columns:

```md
# IoT Beacon Hunt Report

## Summary
- Inventoried devices analyzed: <int>
- Periodic candidate flows: <int>
- Approved periodic flows: <int>
- Suspected beacon flows: <int>
- Devices with suspected beacons: <int>
- Highest risk device: <device_id> (<device_ip>)

## Suspected Beacon Flows
| device_id | device_ip | device_role | dst_ip | protocol | dst_port | packet_count | first_seen_utc | last_seen_utc | mean_iat_seconds | iat_cv | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ... |

## Approved Periodic Flows
| device_id | device_ip | device_role | dst_ip | protocol | dst_port | packet_count | first_seen_utc | last_seen_utc | mean_iat_seconds | iat_cv | classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ... |

## Evidence Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>
```

The evidence bullets must summarize the main suspected destinations, the approved discovery traffic, and the approved time-sync traffic.
