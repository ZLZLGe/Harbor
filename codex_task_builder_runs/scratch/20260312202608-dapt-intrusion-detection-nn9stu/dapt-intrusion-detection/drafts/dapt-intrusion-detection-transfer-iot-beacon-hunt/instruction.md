你会获得两份输入：

- `/root/iot_building_capture.pcap`
- `/root/iot_device_inventory.json`

请分析这份智能楼宇 IoT 抓包，并生成一个 JSON 文件 `/root/iot_beacon_findings.json`。

要求：

- 只输出一个合法 JSON 对象，不要额外写解释文本。
- 所有浮点数统一保留 4 位小数。
- JSON 布尔值必须使用 `true` / `false`。
- 设备归因必须使用清单里的 `device_id`、`ip`、`mac`。

输出结构必须包含以下 6 个顶层对象：

```json
{
  "capture_summary": {
    "total_packets": 0,
    "ip_packets": 0,
    "tcp_packets": 0,
    "udp_packets": 0,
    "arp_packets": 0,
    "broadcast_packets": 0,
    "external_packets": 0,
    "packets_per_minute_avg": 0.0,
    "packets_per_minute_max": 0,
    "peak_to_avg_ratio": 0.0
  },
  "broadcast_noise": {
    "device_id": "",
    "ip": "",
    "mac": "",
    "broadcast_packets": 0,
    "broadcast_share": 0.0,
    "top_channels": ["", "", ""],
    "classification": ""
  },
  "service_diffusion": {
    "device_id": "",
    "ip": "",
    "unique_internal_targets": 0,
    "unique_dst_ports": 0,
    "dst_port_entropy": 0.0,
    "classification": ""
  },
  "beaconing": {
    "device_id": "",
    "src_ip": "",
    "dst_ip": "",
    "dst_port": 0,
    "protocol": "",
    "flow_packets": 0,
    "median_interval_seconds": 0.0,
    "interval_cv": 0.0,
    "classification": ""
  },
  "scan": {
    "device_id": "",
    "src_ip": "",
    "target_ip": "",
    "unique_dst_ports": 0,
    "dst_port_entropy": 0.0,
    "syn_only_ratio": 0.0,
    "classification": ""
  },
  "verdict": {
    "has_beaconing": false,
    "has_scan": false,
    "has_flood_like": false,
    "is_noise_only": false
  }
}
```

按以下规则计算。

基础统计

- `total_packets`: 抓包总包数。
- `ip_packets`: 含有 IPv4 层的包数。
- `tcp_packets`, `udp_packets`, `arp_packets`: 各协议包数。
- `broadcast_packets`: 满足任一条件即计入：
  - 以太网目的 MAC 为 `ff:ff:ff:ff:ff:ff`
  - IPv4 目的地址是组播地址 `224.0.0.0/4`
  - IPv4 目的地址是 `255.255.255.255`
- `external_packets`: 仅统计 IPv4 TCP/UDP 包，且目的地址不是组播/广播；只要源或目的任一端不是 RFC1918 私网地址，就计为外联包。
- `packets_per_minute_avg/max`: 以首包时间为基准，将所有包按 60 秒桶计数，再取平均值和最大值。
- `peak_to_avg_ratio = packets_per_minute_max / packets_per_minute_avg`。

广播噪声归因

- 从设备清单中的设备里，找出发送 `broadcast_packets` 最多的设备。
- `broadcast_share = 该设备的 broadcast_packets / 全部 broadcast_packets`。
- `top_channels` 只统计该设备的广播类包，按计数降序、名称升序取前 3 个：
  - `arp`: ARP 包
  - `mdns`: UDP 目的地址 `224.0.0.251` 且目的端口 `5353`
  - `ssdp`: UDP 目的地址 `239.255.255.250` 且目的端口 `1900`
  - `llmnr`: UDP 目的地址 `224.0.0.252` 且目的端口 `5355`
- `classification` 固定写 `broadcast-noise`。
- 如并列，按源 IP 字符串升序选。

服务扩散归因

- 只看内部 TCP/UDP 包：源和目的都必须是 RFC1918 私网地址，且目的地址不是组播/广播。
- 流键定义为 `(src_ip, dst_ip, src_port, dst_port, protocol)`。
- 只有当反向流 `(dst_ip, src_ip, dst_port, src_port, protocol)` 也存在时，该流才算双向内部流。
- 对每个清单内设备，统计其作为源时：
  - `unique_internal_targets`: 双向内部流覆盖的不同目的 IP 数
  - `unique_dst_ports`: 这些双向内部流中，不同目的端口数
  - `dst_port_entropy`: 该设备在这些双向内部流里，按目的端口频次计算 Shannon entropy
- 选 `unique_internal_targets` 最大的设备；如并列，选 `unique_dst_ports` 更大的；再并列则按源 IP 字符串升序。
- `classification`: 若 `unique_dst_ports < 100` 写 `controller-fanout`，否则写 `suspicious-fanout`。

周期性回连归因

- 只看清单设备发往外部地址的 TCP/UDP 包，按 `(src_ip, dst_ip, dst_port, protocol)` 分组。
- 对每个分组，只使用源设备发出的时间戳，要求该分组至少有 8 个包。
- 相邻时间差构成 `iat`，计算：
  - `median_interval_seconds`
  - `interval_cv = std(iat) / mean(iat)`
- 选择 `interval_cv` 最小的候选；如并列，选 `flow_packets` 更多的；再并列按 `(src_ip, dst_ip, dst_port, protocol)` 字典序。
- 若该候选满足 `interval_cv < 0.15` 且 `20 <= median_interval_seconds <= 90`，则 `classification` 写 `periodic-beacon`，同时 `verdict.has_beaconing = true`；否则写 `not-beaconing` 且 `verdict.has_beaconing = false`。

异常端口扇出归因

- 只看 TCP 包，按源 IP 聚合。
- `syn_only_ratio = SYN 置位且 ACK 未置位的 TCP 包数 / 该源 IP 的 TCP 包总数`。
- `dst_port_entropy` 是该源 IP 目的端口分布的 Shannon entropy。
- 只有同时满足以下 4 条件，才认定为扫描候选：
  - `dst_port_entropy > 6.0`
  - `syn_only_ratio > 0.7`
  - `unique_dst_ports > 100`
  - TCP 包总数 `>= 50`
- 如存在多个候选，依次选择：
  - `unique_dst_ports` 更大
  - `dst_port_entropy` 更大
  - 源 IP 字符串更小
- 输出该候选的 `device_id`、`src_ip`、最常见目的 IP 作为 `target_ip`、`unique_dst_ports`、`dst_port_entropy`、`syn_only_ratio`，并令 `classification = "scan"`、`verdict.has_scan = true`。
- 若无候选，则这些字段写空值或 0，`classification = "none"`，`verdict.has_scan = false`。

总体判定

- `verdict.has_flood_like = (peak_to_avg_ratio > 20)`。
- `verdict.is_noise_only` 仅在 `has_beaconing`、`has_scan`、`has_flood_like` 全为 `false` 时为 `true`，否则为 `false`。
