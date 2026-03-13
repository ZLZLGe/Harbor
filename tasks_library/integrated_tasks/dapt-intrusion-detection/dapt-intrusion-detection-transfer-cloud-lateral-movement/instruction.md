你会获得一份云 VPC 东西向抓包 `/root/cloud_vpc_east_west.pcap`，以及待填写模板 `/root/cloud_lateral_report.csv`。

只填写 `value` 列，保留表头、顺序和所有以 `#` 开头的注释行不变。

除非特别说明，图指标、fan-out、流指标、扫描归因和周期性 C2 归因都只统计同时满足以下条件的报文：

- 含有 IPv4 层
- 源和目的地址都属于 RFC1918 私网

口径如下。

基础统计

- `total_packets`: 抓包中的总报文数
- `total_bytes`: 所有报文长度之和，单位字节
- `protocol_tcp`, `protocol_udp`: TCP / UDP 报文数
- `protocol_ip_total`: 含有 IPv4 层的报文数
- `dominant_protocol`: 在 `tcp` 和 `udp` 中，报文数更多的协议名称；如并列，写 `tcp`

时间 / 突发

- `duration_seconds`: `last_timestamp - first_timestamp`，单位秒
- `packets_per_minute_avg/max/min`: 以首包时间为基准，按 60 秒桶统计每桶报文数，再取平均值 / 最大值 / 最小值
- `burst_minute_index`: 报文数最多的 60 秒桶索引，从 `0` 开始；如并列，取较小索引
- `burst_ratio = packets_per_minute_max / packets_per_minute_avg`

子网图与主机 fan-out

- 子网定义为每个私网 IPv4 地址所在的 `/24`，例如 `10.10.3.15 -> 10.10.3.0/24`
- `num_subnets`: 抓包中出现过的不同 `/24` 私网子网数量
- `subnet_edges`: 不同子网之间唯一有向 `(src_subnet -> dst_subnet)` 边的数量；忽略同子网通信
- `subnet_graph_density`: `subnet_edges / (num_subnets * (num_subnets - 1))`；若 `num_subnets < 2`，写 `0`
- `max_host_fanout`: 任一源 IP 访问过的不同私网目的 IP 最大数量
- `max_host_fanout_ip`: 达到该最大值的源 IP；如并列，取字典序更小的 IP 字符串

5 元组流多样性

- 流键定义为 `(src_ip, dst_ip, src_port, dst_port, protocol)`
- `unique_flows`: 不同 5 元组总数
- `tcp_flows`, `udp_flows`: TCP / UDP 5 元组流数
- `bidirectional_flows`: 若某流的反向键 `(dst_ip, src_ip, dst_port, src_port, protocol)` 也存在，则这一对双向流只计一次
- `flow_diversity_ratio = unique_flows / protocol_ip_total`

横向扫描归因

- 只看内部 TCP 报文，按源 IP 聚合
- `scan_syn_ratio = (SYN 置位且 ACK 未置位的 TCP 报文数) / (该源 IP 的 TCP 报文总数)`
- `scan_dst_port_entropy` 是该源 IP 的目的端口分布 Shannon entropy
- 只有同时满足以下 4 条件，才算扫描候选：
  - `scan_dst_port_entropy > 6.0`
  - `scan_syn_ratio > 0.7`
  - 不同目的端口数 `> 100`
  - 该源 IP 的 TCP 报文总数 `>= 50`
- 若有多个候选，依次选择：
  - 不同目的端口数更大
  - `scan_dst_port_entropy` 更大
  - 源 IP 字符串更小
- `scan_source_ip`: 选中的候选 IP；若无候选则写 `none`
- `scan_unique_dst_ports`: 该候选访问过的不同目的端口数；若无候选则写 `0`
- `scan_syn_ratio`, `scan_dst_port_entropy`: 该候选对应的两个指标；若无候选则写 `0`

周期性 C2 归因

- 为了适配云内大量短连接，候选分组键定义为 `(src_ip, dst_ip, dst_port, protocol)`，不包含源端口
- 对每个候选分组，只使用该方向报文时间戳；要求分组内至少有 8 个报文
- 相邻时间差构成 `iat`，计算：
  - `c2_median_interval_seconds`
  - `c2_interval_cv = std(iat) / mean(iat)`
- 只有 `20 <= c2_median_interval_seconds <= 90` 的分组才参与候选排序
- 选择 `c2_interval_cv` 最小的候选；如并列，选 `c2_flow_packets` 更多的；再并列按 `(src_ip, dst_ip, dst_port, protocol)` 字典序
- `c2_src_ip`, `c2_dst_ip`, `c2_dst_port`, `c2_protocol`, `c2_flow_packets`, `c2_median_interval_seconds`, `c2_interval_cv` 输出该候选的信息
- 若没有任何候选，则 IP / 协议字段写 `none`，端口和数值字段写 `0`

判定

- `has_lateral_scan`: 存在扫描候选则为 `true`，否则为 `false`
- `has_dos_burst`: 若 `burst_ratio > 20` 则为 `true`
- `has_periodic_c2`: 若选中的 C2 候选满足 `c2_interval_cv < 0.15`，则为 `true`
- `is_east_west_benign`: 仅当以上三个判定都为 `false` 时为 `true`

布尔值统一写 `true` 或 `false`。
