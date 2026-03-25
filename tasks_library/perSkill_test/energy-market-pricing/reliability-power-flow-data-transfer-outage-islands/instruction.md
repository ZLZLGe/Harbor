你在区域电网可靠性值班组中，需要对一次风暴后的输电故障场景做快速孤岛评估。调度侧已经给出一份电网快照和一组已确认跳闸的线路，请你根据故障后的剩余拓扑判断系统被切成了哪些孤岛，并汇总每个孤岛的关键规模指标。

输入文件：

- `/root/network.json`：MATPOWER 风格的网络快照。
- `/root/outages.json`：故障场景说明，包含：
  - `scenario_name`
  - `critical_buses`
  - `outaged_branch_indices`

其中，`outaged_branch_indices` 是 `network.json["branch"]` 的 0-based 行号。你必须按这些索引精确移除对应线路；线路端点重复出现时，也不能只按端点模糊匹配。

请生成 `/root/island_assessment.json`，结构如下：

```json
{
  "network_name": "string",
  "outage_scenario": "string",
  "removed_branch_indices": [3, 5, 9, 10, 13],
  "island_count": 3,
  "load_rule": "effective_load_mw = max(Pd, 0)",
  "islands": [
    {
      "island_id": "island_1",
      "bus_numbers": [101, 205, 309, 412],
      "bus_count": 4,
      "total_effective_load_mw": 95.0,
      "total_generation_capacity_mw": 210.0,
      "total_reserve_capacity_mw": 43.5,
      "has_reference_bus": true,
      "disconnected_critical_buses": []
    }
  ]
}
```

计算规则：

1. 构图时只保留 `branch` 中 `status == 1` 的在运线路，然后再移除 `outaged_branch_indices` 指定的那些线路。
2. 把剩余线路视为无向图，按连通分量划分孤岛。`network.json["bus"]` 中的每个母线都必须被分到某个孤岛，即使它在故障后没有任何相邻在运线路。
3. `bus_numbers` 必须按升序输出。
4. `islands` 必须按各自最小母线号升序排序，并依次命名为 `island_1`、`island_2`、……。
5. `total_effective_load_mw`：
   - 对孤岛内每个母线取 `max(Pd, 0)` 后求和。
6. `total_generation_capacity_mw`：
   - 统计孤岛内所有在运机组 `Pmax` 之和。
   - 只计 `gen` 中 `status == 1` 的机组。
7. `total_reserve_capacity_mw`：
   - 统计孤岛内所有在运机组对应的 `reserve_capacity` 之和。
   - `reserve_capacity[i]` 对应 `gen[i]`。
8. `has_reference_bus`：
   - 只要孤岛内存在任一母线类型为 `REF`（MATPOWER 编码 `3`），就记为 `true`，否则为 `false`。
9. `disconnected_critical_buses`：
   - 只从 `outages.json["critical_buses"]` 中取值。
   - 仅当该孤岛 `has_reference_bus == false` 时，才输出该孤岛内的关键母线列表；否则输出空数组。
   - 列表按升序输出。
10. 数值字段统一保留到小数点后 2 位即可。

只需要输出 `island_assessment.json`，不要生成额外文件。
