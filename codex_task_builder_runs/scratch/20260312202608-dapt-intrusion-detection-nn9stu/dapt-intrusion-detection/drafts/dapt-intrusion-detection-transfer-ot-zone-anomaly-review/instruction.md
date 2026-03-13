你会获得两份输入：

- `/root/ot_zone_capture.pcap`
- `/root/ot_asset_inventory.json`

请分析这份 ICS / SCADA 网段抓包，并生成一个 JSON 文件 `/root/ot_zone_risk_assessment.json`。

要求：

- 只输出一个合法 JSON 对象，不要额外写解释文本。
- JSON 顶层必须且只包含以下 6 个对象：
  - `capture_summary`
  - `baseline`
  - `entropy_profile`
  - `cadence_profile`
  - `bidirectional_relationships`
  - `risk_assessment`
- 所有布尔值必须写成 JSON 布尔值 `true` / `false`。
- 所有数组都必须按升序或字典序排序。
- 资产归因必须使用清单中的 `asset_id`、`role`、`ip`、`mac`。
- 如某类候选不存在，字符串字段写 `\"none\"`，数值字段写 `0`，布尔值按规则推导。

输出结构如下：

```json
{
  "capture_summary": {
    "total_packets": 0,
    "ip_packets": 0,
    "tcp_packets": 0,
    "udp_packets": 0,
    "arp_packets": 0,
    "internal_ip_packets": 0,
    "external_ip_packets": 0,
    "duration_seconds": 0.0,
    "active_minutes": 0
  },
  "baseline": {
    "controller_assets": ["", ""],
    "hmi_asset_id": "",
    "engineering_asset_id": "",
    "controller_service_ports": [0, 0],
    "hmi_controller_pairs": 0,
    "engineering_controller_pairs": 0,
    "hmi_poll_median_interval_seconds": 0.0,
    "engineering_maintenance_median_interval_seconds": 0.0
  },
  "entropy_profile": {
    "src_ip_entropy": 0.0,
    "dst_ip_entropy": 0.0,
    "dst_port_entropy": 0.0,
    "eng_station_target_entropy": 0.0,
    "eng_station_dst_port_entropy": 0.0
  },
  "cadence_profile": {
    "control_loop": {
      "src_asset_id": "",
      "dst_asset_id": "",
      "dst_port": 0,
      "protocol": "",
      "flow_packets": 0,
      "median_interval_seconds": 0.0,
      "interval_cv": 0.0
    },
    "maintenance_loop": {
      "src_asset_id": "",
      "dst_asset_id": "",
      "dst_port": 0,
      "protocol": "",
      "flow_packets": 0,
      "median_interval_seconds": 0.0,
      "interval_cv": 0.0
    },
    "external_candidate": {
      "src_asset_id": "",
      "dst_ip": "",
      "dst_port": 0,
      "protocol": "",
      "flow_packets": 0,
      "median_interval_seconds": 0.0,
      "interval_cv": 0.0
    }
  },
  "bidirectional_relationships": {
    "unique_internal_flows": 0,
    "bidirectional_internal_flow_pairs": 0,
    "controller_hmi_bidirectional_pairs": 0,
    "engineering_controller_bidirectional_pairs": 0,
    "unanswered_scan_flows": 0
  },
  "risk_assessment": {
    "scan_source_asset_id": "",
    "scan_target_asset_id": "",
    "scan_unique_dst_ports": 0,
    "scan_dst_port_entropy": 0.0,
    "scan_syn_only_ratio": 0.0,
    "burst_source_asset_id": "",
    "burst_minute_index": 0,
    "burst_packets": 0,
    "burst_ratio": 0.0,
    "beacon_asset_id": "",
    "beacon_dst_ip": "",
    "beacon_dst_port": 0,
    "beacon_protocol": "",
    "beacon_flow_packets": 0,
    "beacon_median_interval_seconds": 0.0,
    "beacon_interval_cv": 0.0,
    "has_scan": false,
    "has_flood_like": false,
    "has_beaconing": false,
    "is_ot_zone_stable": false
  }
}
```

按以下口径计算。

抓包总览

- `total_packets`: 抓包总包数。
- `ip_packets`: 含 IPv4 层且能解析出 TCP 或 UDP 的报文数。
- `tcp_packets`, `udp_packets`, `arp_packets`: 各协议报文数。
- `internal_ip_packets`: `src_ip` 与 `dst_ip` 都在资产清单中的 IPv4 TCP/UDP 报文数。
- `external_ip_packets`: IPv4 TCP/UDP 报文里，只要任一端不在资产清单中就计入。
- `duration_seconds = last_timestamp - first_timestamp`。
- `active_minutes`: 以首包时间为基准，按 60 秒桶统计，只要该桶里至少有 1 个报文就算活跃分钟。

角色基线

- `controller_assets`: 清单中 `role = "controller"` 的 `asset_id`，按字典序排序。
- `hmi_asset_id`: 清单中 `role = "hmi"` 的唯一资产；若有多个，取 `asset_id` 字典序最小者。
- `engineering_asset_id`: 清单中 `role = "engineering-station"` 的唯一资产；若有多个，取 `asset_id` 字典序最小者。
- 内部流定义为同时满足以下条件的 5 元组 `(src_ip, dst_ip, src_port, dst_port, protocol)`：
  - `protocol` 只取 `TCP` 或 `UDP`
  - `src_ip` 与 `dst_ip` 都在资产清单中
- 双向流对：若某流的反向键 `(dst_ip, src_ip, dst_port, src_port, protocol)` 也存在，则这一对只计 1 次。
- `controller_service_ports`: 在双向内部 `TCP` 流里，所有“源角色是 `hmi` 或 `engineering-station`、目的角色是 `controller`”的 `dst_port` 去重后升序输出。
- `hmi_controller_pairs`: 具有至少一个双向内部 `TCP` 流的 `(hmi, controller)` 资产对数量。
- `engineering_controller_pairs`: 具有至少一个双向内部 `TCP` 流的 `(engineering-station, controller)` 资产对数量。
- `hmi_poll_median_interval_seconds`:
  - 只看 `hmi -> controller` 且 `dst_port` 属于 `controller_service_ports` 的内部 `TCP` 方向流；
  - 分组键为 `(src_asset_id, dst_asset_id, dst_port, protocol)`；
  - 只保留报文数 `>= 8` 的分组；
  - 对每个分组，按该方向时间戳计算相邻时间差 `iat` 的中位数；
  - 选择 `interval_cv = std(iat) / mean(iat)` 最小的分组；如并列，取 `flow_packets` 更多的；再并列按分组键字典序；
  - 输出其 `median_interval_seconds`。
- `engineering_maintenance_median_interval_seconds`: 与上面相同，但源角色改为 `engineering-station`，且分组至少要有 `4` 个报文。

熵

- Shannon entropy 定义为 `H(X) = -sum(p(x) * log2(p(x)))`。
- `src_ip_entropy`, `dst_ip_entropy`: 在全部 IPv4 TCP/UDP 报文上计算源 / 目的 IP 熵。
- `dst_port_entropy`: 在全部 IPv4 TCP/UDP 报文上计算目的端口熵。
- `eng_station_target_entropy`: 只看源地址属于 `engineering_asset_id` 对应 IP 的 IPv4 TCP/UDP 报文，计算目的 IP 熵。
- `eng_station_dst_port_entropy`: 同一集合上计算目的端口熵。

节拍

- `cadence_profile.control_loop`: 使用 `hmi_poll_median_interval_seconds` 选中的那一组，完整输出 `src_asset_id`、`dst_asset_id`、`dst_port`、`protocol`、`flow_packets`、`median_interval_seconds`、`interval_cv`。
- `cadence_profile.maintenance_loop`: 使用 `engineering_maintenance_median_interval_seconds` 选中的那一组，输出同样字段。
- `cadence_profile.external_candidate`:
  - 只看源角色是 `engineering-station`、目的 IP 不在资产清单中的 `TCP/UDP` 报文；
  - 分组键为 `(src_asset_id, dst_ip, dst_port, protocol)`；
  - 只保留报文数 `>= 8` 的分组；
  - 选择规则同上：先取 `interval_cv` 最小，再取 `flow_packets` 更多，再按分组键字典序；
  - 输出该分组的字段。

双向关系

- `unique_internal_flows`: 不同内部 5 元组流总数。
- `bidirectional_internal_flow_pairs`: 双向内部流对数量。
- `controller_hmi_bidirectional_pairs`: 双向内部流对中，端点角色集合等于 `{controller, hmi}` 的数量。
- `engineering_controller_bidirectional_pairs`: 双向内部流对中，端点角色集合等于 `{controller, engineering-station}` 的数量。
- `unanswered_scan_flows`:
  - 先按下面“扫描判定”选出扫描候选源；
  - 若存在候选，则统计该源发出的内部 `TCP` 流里，反向流不存在的 5 元组数量；
  - 若无候选则写 `0`。

风险判定

扫描判定

- 只看内部 `TCP` 报文，按源 IP 聚合。
- `scan_syn_only_ratio = SYN 置位且 ACK 未置位的报文数 / 该源 IP 的内部 TCP 报文总数`。
- `scan_dst_port_entropy` 是该源 IP 内部 TCP 目的端口分布的 Shannon entropy。
- `scan_unique_dst_ports` 是该源 IP 内部 TCP 的不同目的端口数。
- 只有同时满足以下 4 个条件，才是扫描候选：
  - `scan_dst_port_entropy > 6.0`
  - `scan_syn_only_ratio > 0.7`
  - `scan_unique_dst_ports > 100`
  - 内部 TCP 报文总数 `>= 50`
- 若有多个候选，依次选择：
  - `scan_unique_dst_ports` 更大
  - `scan_dst_port_entropy` 更大
  - 源 IP 字符串更小
- `scan_target_asset_id`: 取该候选源内部 TCP 报文里最常见的目的资产；如并列，取 `asset_id` 字典序更小。
- 若无候选，`scan_source_asset_id` 与 `scan_target_asset_id` 写 `\"none\"`，数值字段写 `0`，`has_scan = false`。
- 否则输出候选对应字段，并令 `has_scan = true`。

洪泛判定

- 只看资产清单内资产作为源发出的 `TCP/UDP` 报文，按源资产聚合。
- 以整份抓包的首包时间为基准，按 60 秒桶统计每个源资产的发包数。
- 只对该源资产“非空桶”求平均值。
- `burst_ratio = max_bucket_packets / avg_non_empty_bucket_packets`。
- 选 `burst_ratio` 最大的源资产；如并列，取 `burst_packets` 更大的；再并列取 `asset_id` 字典序更小。
- `burst_minute_index`: 该源资产报文数最多的桶索引；如并列，取较小索引。
- 仅当 `burst_ratio > 20` 且 `burst_packets >= 100` 时，`has_flood_like = true`，否则为 `false`。
- 若没有任何源资产发出过 `TCP/UDP` 报文，则字符串字段写 `\"none\"`，数值字段写 `0`，`has_flood_like = false`。

Beaconing 判定

- 使用 `cadence_profile.external_candidate` 选中的分组。
- `has_beaconing = true` 当且仅当同时满足：
  - `20 <= beacon_median_interval_seconds <= 90`
  - `beacon_interval_cv < 0.15`
- 若不存在 `external_candidate`，则 beacon 相关字符串字段写 `\"none\"`，数值字段写 `0`，`has_beaconing = false`。

总体判定

- `is_ot_zone_stable` 仅当 `has_scan`、`has_flood_like`、`has_beaconing` 全为 `false` 时为 `true`，否则为 `false`。
