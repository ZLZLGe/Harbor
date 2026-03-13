你会获得一份分支办公室网段抓包 `/root/branch_segment.pcap`，以及待填写模板 `/root/branch_segment_audit.csv`。

只填写 `value` 列，保留表头、顺序和所有以 `#` 开头的注释行不变。

指标说明如下。

抓包概览
- `total_packets`: 抓包中的总报文数
- `dominant_protocol`: 在 `tcp` / `udp` / `icmp` / `arp` 中，报文数最多的协议名称

协议计数
- `protocol_tcp`, `protocol_udp`, `protocol_icmp`, `protocol_arp`: 各协议报文数
- `protocol_ip_total`: 含有 IPv4 层的报文数

时间 / 速率
- `duration_seconds`: `last_timestamp - first_timestamp`，单位秒
- `packets_per_minute_avg/max/min`: 以首包时间为基准，按 60 秒桶统计每桶报文数，再取平均值 / 最大值 / 最小值

尺寸
- `total_bytes`: 所有报文长度之和，单位字节
- `avg_packet_size`, `min_packet_size`, `max_packet_size`: 报文长度统计

熵
- 对观测频率分布计算 Shannon entropy，忽略缺失值
- `src_ip_entropy`, `dst_ip_entropy`: 源 / 目的 IP 熵
- `src_port_entropy`, `dst_port_entropy`: 源 / 目的端口熵（仅 TCP/UDP）
- `unique_src_ports`, `unique_dst_ports`: 不同源 / 目的端口数量（仅 TCP/UDP）

图指标
- 节点是 IP，边是唯一的有向 `(src_ip -> dst_ip)` 对
- `num_nodes`, `num_edges`: 图中的节点数与唯一有向边数
- `network_density`: `num_edges / (num_nodes * (num_nodes - 1))`，若 `num_nodes < 2` 则为 `0`
- `max_outdegree`: 任一源 IP 连接过的不同目的 IP 最大数量
- `max_indegree`: 任一目的 IP 接收过的不同源 IP 最大数量

时序
- 先按时间排序，再计算相邻报文间隔 `iat`
- `iat_mean`, `iat_variance`
- `iat_cv`: `std(iat) / mean(iat)`；若均值为 `0`，则写 `0`

流指标
- 流键为 `(src_ip, dst_ip, src_port, dst_port, protocol)`
- `unique_flows`: 不同 5 元组总数
- `tcp_flows`, `udp_flows`: TCP / UDP 流数
- `bidirectional_flows`: 若某流的反向键 `(dst, src, dst_port, src_port, protocol)` 也存在，则记为双向流；一对双向流只计一次

疑似扫描源归因
- 只对 TCP 报文按源 IP 聚合
- `syn_only_ratio = (SYN 置位且 ACK 未置位的 TCP 报文数) / (该源 IP 的 TCP 报文总数)`
- `suspected_scanner_ip`: 从满足以下全部条件的源 IP 中选出疑似扫描源
  - 该源 IP 的 `dst_port_entropy > 6.0`
  - `syn_only_ratio > 0.7`
  - `unique dst ports > 100`
  - 该源 IP 的 TCP 报文总数 `>= 50`
- 若有多个候选，依次选择：
  - `unique dst ports` 更大的
  - 若仍并列，`dst_port_entropy` 更大的
  - 若仍并列，取字典序更小的 IP 字符串
- 若没有候选，则 `suspected_scanner_ip` 写 `none`，其余 3 个疑似源指标写 `0`
- `suspected_scanner_unique_dst_ports`: 该疑似源访问过的不同目的端口数
- `suspected_scanner_syn_ratio`: 该疑似源的 `syn_only_ratio`
- `suspected_scanner_dst_port_entropy`: 该疑似源目的端口分布的 Shannon entropy

威胁判定
- `has_port_scan`: 只要存在任一满足上述 4 个条件的源 IP，则为 `true`，否则 `false`
- `has_dos_pattern`: 若 `packets_per_minute_max / packets_per_minute_avg > 20`，则为 `true`
- `has_beaconing`: 若 `iat_cv < 0.5`，则为 `true`
- `is_traffic_benign`: 仅当以上三个威胁标记全部为 `false` 时为 `true`

布尔值统一写 `true` 或 `false`。
