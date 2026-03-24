你在复核一份办公室出口 DNS 抓包，怀疑有主机通过超长子域做周期性回连。

请分析 `/root/pcaps/dns_resolver_mix.pcap`，并在 `/root/dns_beacon_clusters.csv` 输出所有可疑聚类。CSV 必须包含且仅包含以下表头，顺序不能变：

```text
src_host,suspicious_base_domain,query_count,longest_query_name_len,first_seen_utc
```

判定规则：

1. 只统计 DNS 请求包，不统计响应包。
2. 只统计 `A` 记录查询。
3. 把同一 `src_host` 对同一基域名的查询视为一个候选聚类。
4. 基域名按查询名最后两个标签计算，例如 `a.b.example.net` 的基域名是 `example.net`。
5. 只有当该候选聚类满足以下全部条件时，才输出一行：
   - 查询次数至少为 4。
   - 该聚类内每个查询名的总长度都至少为 45 个字符。
   - 按时间排序后，相邻两次查询的间隔都在 50 到 80 秒之间（含边界）。
6. `longest_query_name_len` 是该聚类中最长查询名的字符数，查询名不包含结尾的点号。
7. `first_seen_utc` 使用该聚类首次出现时间，格式固定为 `YYYY-MM-DDTHH:MM:SSZ`。

输出要求：

- 结果按 `first_seen_utc` 升序排序；如果时间相同，再按 `src_host` 升序排序。
- 只输出满足条件的可疑聚类，不要加入说明文字或 Markdown。
- 除表头外，每一行都必须对应抓包中的真实查询。
