你在储能规划组负责做一轮候选并网点初筛。团队已经从同一份电网快照里整理出一批待评估站点，希望你先基于网络拓扑和静态设备数据给出一个可复核的排序结果，供后续工程设计继续筛选。

输入文件：

- `network.json`：MATPOWER 风格的网络快照。
- `candidate_sites.csv`：候选站点列表，至少包含以下列：
  - `candidate_id`
  - `site_name`
  - `interconnection_bus`
  - 其他列如果存在，可以忽略。

请生成 `battery_site_ranking.csv`，并严格使用以下表头顺序：

```csv
candidate_id,site_name,interconnection_bus,connected_bus_degree,connectivity_label,two_hop_bus_count,two_hop_effective_load_mw,adjacent_line_rating_sum_mw,same_bus_generation_capacity_mw,same_bus_available_reserve_mw,screening_score,priority_rank
```

计算规则：

1. `interconnection_bus` 必须与 `network.json["bus"]` 中的母线号精确匹配。母线号不是连续编号，不能把它当作 1-based 或 0-based 行号。
2. 所有拓扑统计只使用在运线路，即 `branch` 中 `status == 1` 的行。线路按无向图处理。
3. `connected_bus_degree`：
   - 统计候选母线通过在运线路连接到的不同相邻母线数量。
   - 如果存在并联线路，只按相邻母线去重后计数。
4. `connectivity_label` 由 `connected_bus_degree` 映射得到：
   - `0 -> isolated`
   - `1 -> radial`
   - `2` 或 `3 -> corridor`
   - `>= 4 -> hub`
5. `two_hop_bus_count` 与 `two_hop_effective_load_mw` 基于候选母线的 2-hop 邻域：
   - 集合中包含候选母线自己。
   - 再加入通过 1 条或 2 条在运线路可以到达的所有母线。
   - `two_hop_bus_count` 为该集合内母线数。
   - `two_hop_effective_load_mw` 为该集合内所有母线 `max(Pd, 0)` 之和。
6. `adjacent_line_rating_sum_mw`：
   - 对所有与候选母线直接相连的在运线路，求 `rateA`（`branch` 第 6 列）的总和。
   - 这里并联线路不去重，每一条线路都要单独累加。
7. `same_bus_generation_capacity_mw`：
   - 统计候选母线本身所有在运机组 `Pmax` 之和。
   - 只计 `gen` 中 `status == 1` 的机组。
8. `same_bus_available_reserve_mw`：
   - 统计候选母线本身所有在运机组对应的 `reserve_capacity` 之和。
   - `reserve_capacity[i]` 与 `gen[i]` 一一对应。
9. `screening_score` 固定按下面公式计算：
   - `two_hop_effective_load_mw / 100`
   - `+ adjacent_line_rating_sum_mw / 5000`
   - `+ same_bus_available_reserve_mw / 10`
   - `- same_bus_generation_capacity_mw / 200`
10. 排序规则：
   - 按 `screening_score` 从高到低排序。
   - 若分数相同，按 `candidate_id` 字典序升序。
   - 输出文件中的 `priority_rank` 从 1 开始连续编号，且行顺序必须已经按这个排名排好。
11. 数值格式：
   - `two_hop_effective_load_mw`
   - `adjacent_line_rating_sum_mw`
   - `same_bus_generation_capacity_mw`
   - `same_bus_available_reserve_mw`
   以上 4 列保留 2 位小数。
   - `screening_score` 保留 6 位小数。
   - `interconnection_bus`、`connected_bus_degree`、`two_hop_bus_count`、`priority_rank` 输出为整数。

只需要输出 `battery_site_ranking.csv`，不要生成额外文件。
