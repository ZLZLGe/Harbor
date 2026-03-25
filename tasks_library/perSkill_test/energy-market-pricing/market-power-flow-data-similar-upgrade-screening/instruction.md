你在区域电力市场团队中负责做拥塞升级项目的前置筛选。团队已经从同一份电网快照里挑出若干条候选输电约束，希望你先做一次纯数据层面的预筛选，帮助后续工程师优先查看最值得升级的约束。

输入文件：

- `/root/network.json`：MATPOWER 风格的网络快照。
- `/root/candidate_constraints.json`：候选约束列表。每个候选项都给出 `constraint_id` 和 `branch_index`。这里的 `branch_index` 是 `network.json["branch"]` 的 0-based 行号；即使两条线路端点相同，也必须按这个索引精确定位对应线路。

请生成 `/root/constraint_screening.json`，结构如下：

```json
{
  "network_name": "string",
  "candidate_dataset": "string",
  "candidate_count": 7,
  "effective_load_rule": "effective_load_mw = max(Pd, 0)",
  "score_formula": "combined_one_hop_effective_load_mw / line_rating_mw + 0.1 * (from_bus_degree + to_bus_degree) + 0.5 * controllable_endpoint_count - 0.0002 * combined_one_hop_generation_capacity_mw - 0.0005 * combined_one_hop_reserve_capacity_mw",
  "screened_constraints": [
    {
      "constraint_id": "string",
      "branch_index": 241,
      "from_bus": 1930,
      "to_bus": 2363,
      "line_rating_mw": 9.0,
      "from_bus_type": {"code": 1, "label": "PQ"},
      "to_bus_type": {"code": 2, "label": "PV"},
      "from_bus_degree": 12,
      "to_bus_degree": 15,
      "from_endpoint_summary": {
        "effective_load_mw": 452.58,
        "generation_capacity_mw": 0.0,
        "reserve_capacity_mw": 0.0
      },
      "to_endpoint_summary": {
        "effective_load_mw": 0.0,
        "generation_capacity_mw": 1471.0,
        "reserve_capacity_mw": 132.57182
      },
      "from_one_hop_summary": {
        "bus_count": 13,
        "effective_load_mw": 4136.32,
        "generation_capacity_mw": 1471.0,
        "reserve_capacity_mw": 132.57182
      },
      "to_one_hop_summary": {
        "bus_count": 16,
        "effective_load_mw": 4818.08,
        "generation_capacity_mw": 1471.0,
        "reserve_capacity_mw": 132.57182
      },
      "combined_one_hop_summary": {
        "bus_count": 20,
        "effective_load_mw": 5733.81,
        "generation_capacity_mw": 1471.0,
        "reserve_capacity_mw": 132.57182
      },
      "controllable_endpoint_count": 1,
      "exposure_score": 639.929514,
      "priority_rank": 1
    }
  ]
}
```

计算规则：

1. `bus` 的类型编码按 MATPOWER 约定解释：`1 -> PQ`，`2 -> PV`，`3 -> REF`，`4 -> NONE`。
2. `line_rating_mw` 使用对应 `branch` 行的 `rateA`（第 6 列）。
3. 母线度数只统计 `branch` 中 `status == 1` 的在运线路，按无向图计算。
4. 端点汇总：
   - `effective_load_mw = max(Pd, 0)`，其中 `Pd` 来自对应母线行。
   - `generation_capacity_mw` 为该母线所有在运机组 `Pmax` 之和。
   - `reserve_capacity_mw` 为该母线所有在运机组对应 `reserve_capacity` 之和。
5. `from_one_hop_summary` / `to_one_hop_summary`：
   - 使用“端点自己 + 与它直接相连的所有母线”的集合。
   - 在这个集合上分别汇总 `effective_load_mw`、`generation_capacity_mw`、`reserve_capacity_mw`，并给出集合内母线数 `bus_count`。
6. `combined_one_hop_summary`：
   - 取 `from` 端与 `to` 端两个 1-hop 集合的并集后，再做同样的汇总。
7. `controllable_endpoint_count`：
   - 统计两个端点里，母线类型属于 `PV` 或 `REF` 的个数。
8. `exposure_score` 公式固定为：
   - `combined_one_hop_effective_load_mw / line_rating_mw`
   - `+ 0.1 * (from_bus_degree + to_bus_degree)`
   - `+ 0.5 * controllable_endpoint_count`
   - `- 0.0002 * combined_one_hop_generation_capacity_mw`
   - `- 0.0005 * combined_one_hop_reserve_capacity_mw`
9. 数值格式：
   - `line_rating_mw`、所有 `effective_load_mw`、所有 `generation_capacity_mw` 保留 2 位小数。
   - 所有 `reserve_capacity_mw` 与 `exposure_score` 保留 6 位小数。
10. 排序规则：
   - 按 `exposure_score` 从高到低排序。
   - 若分数相同，按 `constraint_id` 字典序升序。
   - 输出中的 `priority_rank` 从 1 开始连续编号，且 `screened_constraints` 必须已经按这个顺序排好。

只需要输出 `constraint_screening.json`，不要生成额外文件。
