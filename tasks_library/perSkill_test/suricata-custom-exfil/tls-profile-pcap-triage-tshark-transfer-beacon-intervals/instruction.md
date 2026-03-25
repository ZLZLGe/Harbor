你需要分析一份以 TLS 握手为主的抓包，并仅根据握手元数据与连接时间分布识别周期性 beacon。

输入文件固定为 `/workspace/inputs/tls_handshake_mix.pcap`。

请生成 `/workspace/outputs/tls_beacon_profile.json`。输出必须是一个 JSON 对象，并且包含键 `beacons`。`beacons` 必须是数组，且按 `client_ip` 升序排列；如果 `client_ip` 相同，再按 `target_ip`、`target_port`、`sni` 升序排列。

只把同时满足以下条件的连接组视为 beacon：

- 只统计客户端发出的 TLS `Client Hello` 握手，并且该握手必须带有非空 SNI
- 以 `(client_ip, target_ip, target_port, sni)` 作为分组键
- 同一分组的连接次数至少为 5
- 把该分组内各次 `Client Hello` 的时间戳按先后排序后，计算相邻两次之间的秒数差
- 如果这些时间差都能落在某一个共同周期的 `±3` 秒内，则该分组命中 beacon
- `approx_period_seconds` 取这些时间差的中位数，并四舍五入到最接近的整数秒

`beacons` 数组中的每个元素都必须包含以下字段：

- `client_ip`：字符串，客户端 IP
- `target_ip`：字符串，目标 IP
- `target_port`：整数，目标端口
- `sni`：字符串，TLS 握手里的 SNI
- `connection_count`：整数，该分组命中的连接次数
- `approx_period_seconds`：整数，按上面规则计算出的近似周期秒数
- `evidence`：非空字符串，简要说明为何判定为 beacon；至少要体现连接次数和周期依据

输出要求：

- 只输出真正命中的 beacon 分组，不要把普通浏览流量、缺少 SNI 的握手、连接次数不足的分组，或时间间隔不稳定的分组写进去
- 不要添加题目未要求的顶层必填字段
- 不要输出额外说明文字；文件内容必须是合法 JSON
