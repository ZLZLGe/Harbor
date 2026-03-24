你在沿海输电公司的风暴恢复值班席位上，需要基于灾后停运清单快速判断哪些区域仍然构成带电孤岛，哪些负荷已经因为拓扑断开而失供。请读取 `network.json`、`storm_outages.json` 和 `critical_loads.json`，生成 `restoration_islands_report.json`。

输入说明：

- `network.json` 是 MATPOWER 风格案例，包含 `bus`、`gen`、`branch`、`gencost` 等数组。
- `storm_outages.json` 给出本次风暴造成的停运元件：
  - `branch_outages` 中的 `(from_bus, to_bus)` 表示该支路在灾后强制停运。
  - `generator_outages` 中的 `id` 使用 `gen` 数组的 1-based 行号；这些机组即使原始 `GEN_STATUS = 1` 也要视为不可用。
- `critical_loads.json` 给出需要重点统计的关键负荷母线。

计算规则：

- 必须按实际 `BUS_I` 建立映射，不能把数组下标直接当母线编号。
- 支路连通性只保留满足以下条件的设备：
  - 原始 `BR_STATUS = 1`
  - 不在 `storm_outages.json.branch_outages` 中
- 可用发电只统计同时满足以下条件的机组：
  - 原始 `GEN_STATUS = 1`
  - 不在 `storm_outages.json.generator_outages` 中
  - `PMAX > 0`
- 网络连通性按无向图处理；每个连通分量都是一个候选组件。
- 某个连通分量只要 `available_generation_MW > 0`，就视为“带电孤岛”；否则视为“失电组件”。
- `load_MW` 与 `load_MVAr` 都按正负荷统计，即分别对每个母线使用 `max(Pd, 0)`、`max(Qd, 0)` 后求和。
- `available_generation_MW` 按该连通分量内可用机组的 `PMAX` 求和，不使用当前 `PG`。
- `generation_margin_MW = available_generation_MW - load_MW`。
- 关键负荷覆盖只按拓扑是否位于带电孤岛中判断，不需要进一步做潮流计算、机组分配或可行性校核。

输出 JSON 结构必须为：

```json
{
  "summary": {
    "total_bus_count": 0,
    "active_branch_count": 0,
    "available_generator_count": 0,
    "energized_island_count": 0,
    "de_energized_component_count": 0,
    "topology_disconnected_load_MW": 0.0,
    "topology_disconnected_load_MVAr": 0.0
  },
  "critical_load_coverage": {
    "total_count": 0,
    "served_count": 0,
    "unserved_count": 0,
    "served_MW": 0.0,
    "unserved_MW": 0.0,
    "served_bus_ids": [],
    "unserved_bus_ids": []
  },
  "energized_islands": [
    {
      "island_id": "island_1",
      "representative_bus_ids": [0],
      "bus_count": 0,
      "load_MW": 0.0,
      "load_MVAr": 0.0,
      "available_generation_MW": 0.0,
      "generation_margin_MW": 0.0,
      "online_generator_count": 0,
      "generator_bus_ids": [0],
      "critical_load_bus_ids": [0],
      "critical_load_MW": 0.0
    }
  ],
  "de_energized_components": [
    {
      "component_id": "component_1",
      "representative_bus_ids": [0],
      "bus_count": 0,
      "load_MW": 0.0,
      "load_MVAr": 0.0,
      "critical_load_bus_ids": [0],
      "critical_load_MW": 0.0
    }
  ]
}
```

排序与编号要求：

- `energized_islands` 按 `load_MW` 降序排序；若相同，再按 `available_generation_MW` 降序；若仍相同，再按该组件最小母线编号升序。排序后依次编号为 `island_1`、`island_2`、……
- `de_energized_components` 按 `load_MW` 降序排序；若相同，再按该组件最小母线编号升序。排序后依次编号为 `component_1`、`component_2`、……
- `representative_bus_ids` 为该组件内升序后的前 10 个母线编号；如果不足 10 个，则全部输出。
- `generator_bus_ids` 和 `critical_load_bus_ids` 都按升序输出。

补充要求：

- `summary.topology_disconnected_load_MW` 与 `summary.topology_disconnected_load_MVAr` 分别是所有失电组件的正负荷总和。
- `critical_load_coverage.served_bus_ids` 与 `critical_load_coverage.unserved_bus_ids` 都按升序输出。
- 输出中所有功率值都使用 MW 或 MVAr。
