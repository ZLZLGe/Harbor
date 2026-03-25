你在风暴后的港区孤网恢复组做复盘。调度负责人想知道：如果抢修队把一条联络线修复回来，哪些母线的边际供电价值会变化，关键避难所的恢复价值是否明显改善，以及原本分裂的价格区域有没有被打通。

输入文件有两个：

- `microgrid_assets.json`：包含风暴后仍可用的母线、负荷惩罚、可调度电源和基线可用线路。
- `repair_plan.json`：包含待修复联络线、需要重点比较的避难所母线，以及用于判断价格分裂是否消除的母线对。

请分别求解两个场景：

1. `baseline`：只使用 `microgrid_assets.json` 中的 `baseline_lines`。
2. `tie_repaired`：在 `baseline_lines` 基础上，再加入 `repair_plan.json` 中的 `repairable_tie_line`。

恢复模型为单小时优化，约束与目标如下：

1. 每台可调度电源的出力在 `0` 到 `max_output_mw` 之间，边际成本为 `marginal_cost_dollars_per_mwh`。
2. 每条线路都是定向线路，功率只能沿 `from_bus -> to_bus` 方向传输，且不超过 `limit_mw`。
3. 每个有负荷的母线可以恢复 `0` 到 `demand_mw` 之间的负荷。
4. 每个母线都要满足功率平衡：本地发电 + 流入 = 已恢复负荷 + 流出。
5. 目标是最小化 `总发电成本 + 总未恢复负荷惩罚`，其中每个母线的未恢复负荷惩罚为：
   `unserved_penalty_dollars_per_mwh * (demand_mw - restored_load_mw)`。

价格定义：

- 某母线的 `marginal_service_value_dollars_per_mwh`，表示在最优解附近，向该母线额外提供 `1 MWh` 电量可使目标值下降多少美元。
- 如果你的建模工具对节点平衡等式约束采用相反符号，请自行换算成上面这个“正值表示额外供电有价值”的定义。

价格孤岛定义：

- 先把每个母线的边际供电价值四舍五入到 2 位小数。
- 只统计 `demand_mw > 0` 的负荷母线。
- 数值相同的负荷母线视为同一个价格孤岛。

请生成 `/root/restoration_service_prices.json`，结构必须为：

```json
{
  "baseline": {
    "total_restored_load_mw": 0.0,
    "price_island_count": 0,
    "bus_marginal_service_values": [
      {
        "bus_id": "harbor_clinic",
        "marginal_service_value_dollars_per_mwh": 0.0
      }
    ],
    "price_islands": [
      {
        "marginal_service_value_dollars_per_mwh": 0.0,
        "buses": ["harbor_clinic"]
      }
    ]
  },
  "tie_repaired": {
    "total_restored_load_mw": 0.0,
    "price_island_count": 0,
    "bus_marginal_service_values": [
      {
        "bus_id": "harbor_clinic",
        "marginal_service_value_dollars_per_mwh": 0.0
      }
    ],
    "price_islands": [
      {
        "marginal_service_value_dollars_per_mwh": 0.0,
        "buses": ["harbor_clinic"]
      }
    ]
  },
  "restoration_comparison": {
    "restored_load_gain_mw": 0.0,
    "shelter_value_changes": [
      {
        "bus_id": "east_shelter",
        "baseline_marginal_service_value_dollars_per_mwh": 0.0,
        "tie_repaired_marginal_service_value_dollars_per_mwh": 0.0,
        "change_dollars_per_mwh": 0.0
      }
    ],
    "repair_line_eliminated_original_price_split": true
  }
}
```

额外要求：

- `bus_marginal_service_values` 必须覆盖所有母线，并按 `bus_id` 升序排列。
- `price_islands` 只统计负荷母线，且按 `marginal_service_value_dollars_per_mwh` 升序排列；同一孤岛中的 `buses` 按 `bus_id` 升序排列。
- `price_island_count` 必须等于 `price_islands` 的数量。
- `restored_load_gain_mw = tie_repaired.total_restored_load_mw - baseline.total_restored_load_mw`。
- `shelter_value_changes` 必须覆盖 `repair_plan.json` 中 `observed_shelter_buses` 列出的所有母线，并按 `bus_id` 升序排列。
- `change_dollars_per_mwh = tie_repaired_marginal_service_value_dollars_per_mwh - baseline_marginal_service_value_dollars_per_mwh`。
- `repair_line_eliminated_original_price_split` 的判定只看 `repair_plan.json` 中 `split_check_pair` 给出的两个母线：
  - 若这两个母线在 `baseline` 的边际供电价值不同；
  - 且在 `tie_repaired` 的边际供电价值相同；
  - 则该字段为 `true`，否则为 `false`。
- 所有 MW 和金额都保留 2 位小数。
