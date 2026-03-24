你在车队电动化项目的并网前筛选阶段，需要先从一批候选接入母线里选出更适合建设充电站的站点。请读取 `network.json` 与 `candidate_buses.json`，生成 `ev_depot_screen.json`。

输入说明：

- `network.json` 是 MATPOWER 风格案例，包含 `bus`、`gen`、`branch`、`gencost` 等数组。
- 这个派生任务里的母线行顺序没有按编号排序，必须按 `BUS_I` 建立映射，不能把数组位置当成母线编号。
- `candidate_buses.json` 给出车队充电站需求、打分权重、状态阈值以及候选接入母线列表。

只统计投运设备：

- 发电机只统计 `GEN_STATUS = 1`。
- 支路只统计 `BR_STATUS = 1`。
- 支路容量相关指标使用 `RATE_A`；当 `RATE_A <= 0` 时按 0 处理。

对每个候选母线，先计算下面这些原始指标：

- `base_kV`：母线 `BASE_KV`。
- `existing_load_MW`：该母线的 `max(PD, 0)`。
- `same_bus_generation_margin_MW`：同母线所有在线机组的 `sum(max(PMAX - PG, 0))`。
- `adjacent_branch_count`：与该母线直接相连的在线支路条数。
- `adjacent_branch_capacity_MVA_sum`：与该母线直接相连的在线支路的 `sum(max(RATE_A, 0))`。
- `max_adjacent_branch_MVA`：与该母线直接相连的在线支路里 `max(max(RATE_A, 0))`。
- `one_hop_neighbor_count`：通过在线支路可直接到达的唯一相邻母线数。
- `one_hop_115kV_plus_neighbor_count`：上述相邻母线里，`BASE_KV >= preferred_voltage_kV` 的数量。
- `one_hop_generator_bus_count`：上述相邻母线里，存在至少一台在线且 `PMAX - PG > 0` 的机组的母线数量。
- `one_hop_total_neighbor_load_MW`：上述相邻母线的 `sum(max(PD, 0))`。

打分规则：

- 只在候选母线集合内部做归一化。
- 对“越大越好”的指标使用：

```text
normalized = (value - min_value) / (max_value - min_value)
```

- 对 `existing_load_MW` 使用“越小越好”的归一化：

```text
normalized = (max_value - value) / (max_value - min_value)
```

- 如果某个指标在候选集合中的 `max_value == min_value`，则该指标的归一化值记为 `1.0`。
- `one_hop_topology` 定义为：

```text
0.5 * normalized(one_hop_neighbor_count)
+ 0.3 * normalized(one_hop_115kV_plus_neighbor_count)
+ 0.2 * normalized(one_hop_generator_bus_count)
```

- 总分定义为：

```text
score = 100 * (
    w_voltage_level * normalized(base_kV)
  + w_existing_load * normalized(existing_load_MW, lower_is_better)
  + w_same_bus_generation_margin * normalized(same_bus_generation_margin_MW)
  + w_adjacent_branch_capacity * normalized(adjacent_branch_capacity_MVA_sum)
  + w_one_hop_topology * one_hop_topology
)
```

- 所有分数与归一化分项都保留 4 位小数。

状态判定：

- 若 `base_kV >= preferred_voltage_kV` 且 `score >= preferred_min_score`，状态为 `preferred`。
- 否则，若 `base_kV >= minimum_voltage_kV` 且 `score >= conditional_min_score`，状态为 `conditional`。
- 其余为 `reject`。

排序要求：

- `ranked_candidates` 按 `score` 降序排序。
- 若分数相同，再按 `adjacent_branch_capacity_MVA_sum` 降序。
- 若仍相同，再按 `bus` 升序。
- 排序后 `rank` 从 1 开始连续编号。
- `recommended_bus_ids` 仅包含状态为 `preferred` 的候选母线编号，顺序与排序结果一致。

输出 JSON 结构必须为：

```json
{
  "screening_context": {
    "depot_name": "",
    "depot_peak_demand_MW": 0.0,
    "minimum_voltage_kV": 0.0,
    "preferred_voltage_kV": 0.0,
    "strong_branch_capacity_threshold_MVA": 0.0,
    "candidate_count": 0
  },
  "status_summary": {
    "preferred_count": 0,
    "conditional_count": 0,
    "reject_count": 0,
    "recommended_bus_ids": [0]
  },
  "ranked_candidates": [
    {
      "rank": 1,
      "bus": 0,
      "site_code": "",
      "score": 0.0,
      "status": "preferred",
      "score_breakdown": {
        "voltage_level": 0.0,
        "existing_load": 0.0,
        "same_bus_generation_margin": 0.0,
        "adjacent_branch_capacity": 0.0,
        "one_hop_topology": 0.0
      },
      "screening_flags": {
        "meets_minimum_voltage": true,
        "meets_preferred_voltage": true,
        "has_same_bus_generation_margin": true,
        "strong_branch_capacity_proxy": true
      },
      "summary": {
        "base_kV": 0.0,
        "existing_load_MW": 0.0,
        "same_bus_generation_margin_MW": 0.0,
        "adjacent_branch_count": 0,
        "adjacent_branch_capacity_MVA_sum": 0.0,
        "max_adjacent_branch_MVA": 0.0,
        "one_hop_neighbor_count": 0,
        "one_hop_115kV_plus_neighbor_count": 0,
        "one_hop_generator_bus_count": 0,
        "one_hop_total_neighbor_load_MW": 0.0
      }
    }
  ]
}
```

补充要求：

- `screening_flags.strong_branch_capacity_proxy` 的判定规则为 `adjacent_branch_capacity_MVA_sum >= strong_branch_capacity_threshold_MVA`。
- `screening_flags.has_same_bus_generation_margin` 的判定规则为 `same_bus_generation_margin_MW > 0`。
- 所有 MW、MVA、kV 数值都保留 4 位小数。
