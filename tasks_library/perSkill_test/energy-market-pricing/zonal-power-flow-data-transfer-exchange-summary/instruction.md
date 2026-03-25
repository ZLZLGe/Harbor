你在调度数据组负责把一份静态电网快照整理成“运行分区联络概览”，供交接班时快速查看。团队额外提供了一份运行分区映射文件；注意，这份映射才是本题的权威分区定义，不能直接拿 `network.json` 里 `bus` 表自带的第 11 列规划分区字段替代。

输入文件：

- `/root/network.json`：MATPOWER 风格的网络快照。
- `/root/zones.json`：运行分区映射，结构如下：
  - `dataset_name`
  - `zone_definitions`：数组；每项包含 `zone_id` 与 `zone_name`
  - `bus_to_zone`：对象；键是母线号字符串，值是 `zone_id`

请生成 `/root/zone_exchange_summary.json`，结构如下：

```json
{
  "network_name": "string",
  "zone_dataset": "string",
  "zone_count": 4,
  "interzonal_interface_count": 6,
  "effective_load_rule": "effective_load_mw = max(Pd, 0)",
  "zones": [
    {
      "zone_id": "north_hub",
      "zone_name": "North Hub",
      "bus_count": 3,
      "total_effective_load_mw": 73.5,
      "total_generation_capacity_mw": 242.5,
      "total_reserve_capacity_mw": 46.75,
      "reference_bus_numbers": [145],
      "has_reference_bus": true
    }
  ],
  "interzonal_interfaces": [
    {
      "interface_id": "east_valley__north_hub",
      "from_zone": "east_valley",
      "to_zone": "north_hub",
      "active_branch_count": 2,
      "total_rating_mw": 221.25
    }
  ]
}
```

计算规则：

1. 分区必须以 `zones.json["bus_to_zone"]` 为准；不要使用 `network.json["bus"]` 中自带的规划分区字段替代。
2. `zones` 数组必须严格按照 `zones.json["zone_definitions"]` 的顺序输出。
3. `bus_count` 是映射到该分区的母线数量。
4. `total_effective_load_mw`：
   - 对分区内每个母线取 `max(Pd, 0)` 后求和。
5. `total_generation_capacity_mw`：
   - 统计分区内所有在运机组 `Pmax` 之和。
   - 只计 `gen` 中 `status == 1` 的机组。
6. `total_reserve_capacity_mw`：
   - 统计分区内所有在运机组对应的 `reserve_capacity` 之和。
   - `reserve_capacity[i]` 与 `gen[i]` 一一对应。
7. `reference_bus_numbers`：
   - 统计分区内所有母线类型为 `REF` 的母线号。
   - 按升序输出。
8. `has_reference_bus`：
   - 只要 `reference_bus_numbers` 非空，就为 `true`，否则为 `false`。
9. `interzonal_interfaces`：
   - 只统计 `branch` 中 `status == 1` 的在运线路。
   - 只有当线路两端母线映射到不同 `zone_id` 时，才算跨区联络线。
   - 并联线路要分别计数，不能去重。
   - 每个无向分区对只输出 1 条记录。
10. `from_zone` 与 `to_zone`：
   - 对每个跨区分区对，按 `zone_id` 字典序较小者放入 `from_zone`，较大者放入 `to_zone`。
   - `interface_id` 固定写为 `from_zone + "__" + to_zone`。
11. `active_branch_count` 是该分区对之间所有在运跨区线路的数量。
12. `total_rating_mw` 使用这些线路的 `rateA`（`branch` 第 6 列）求和。
13. `interzonal_interfaces` 必须按 `(from_zone, to_zone)` 字典序升序输出。
14. 顶层 `zone_count` 等于 `zones` 数组长度；`interzonal_interface_count` 等于 `interzonal_interfaces` 数组长度。
15. 所有 MW 数值字段统一保留到小数点后 2 位；计数字段输出为整数。

只需要输出 `zone_exchange_summary.json`，不要生成额外文件。
