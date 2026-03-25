你在一家电动公交车场的夜间运营组做分时电价复盘。运营经理怀疑南侧车位群在晚高峰前后的补能价格被馈线瓶颈抬高，因此想比较临时旁路电缆投运前后的两次网络约束充电调度结果。

输入文件有两个：

- `depot_feeder.json`：包含车场馈线节点、主馈线转运能力、24 小时主电源购电价，以及临时旁路电缆方案。
- `charging_demand.json`：包含各充电分区所属节点和 24 小时充电需求。

请分别求解两个场景：

1. `baseline`：只使用 `depot_feeder.json` 里的基线馈线。
2. `bypass_cable`：在基线馈线基础上，再加入 `temporary_bypass` 描述的临时旁路电缆。

调度模型如下：

1. 每个小时独立求解。
2. 主电源从 `substation` 节点注入，注入上限为 `grid_connection.max_import_mwh_per_hour`，边际成本为该小时的 `hourly_energy_price_dollars_per_MWh`。
3. 每个充电分区还可以使用本分区的就地应急补能，边际成本统一为 `local_backup_price_dollars_per_MWh`。就地补能只抵消本分区需求，不回送到馈线。
4. 馈线有方向，功率只能沿 `baseline_lines` 和 `temporary_bypass` 给定方向向下游输送，且每条线路都受 `limit_mwh_per_hour` 约束。
5. 对每个节点、每个小时都要满足功率平衡。

价格定义：

- 某分区在某小时的节点充电边际价格，定义为该分区所属节点在该小时节点平衡约束的影子价格，单位为 `$ / MWh`。

请生成 `/root/charging_tariffs.json`，结构必须为：

```json
{
  "baseline": {
    "total_charging_cost_dollars": 0.0,
    "zone_hourly_tariffs": [
      {
        "zone": "north_yard",
        "bus_id": "north",
        "tariffs_dollars_per_MWh": [26.0, 26.0, 26.0]
      }
    ],
    "peak_hour_by_zone": [
      {
        "zone": "north_yard",
        "bus_id": "north",
        "peak_hour": 16,
        "peak_tariff_dollars_per_MWh": 72.0
      }
    ]
  },
  "bypass_cable": {
    "total_charging_cost_dollars": 0.0,
    "zone_hourly_tariffs": [
      {
        "zone": "north_yard",
        "bus_id": "north",
        "tariffs_dollars_per_MWh": [26.0, 26.0, 26.0]
      }
    ],
    "peak_hour_by_zone": [
      {
        "zone": "north_yard",
        "bus_id": "north",
        "peak_hour": 16,
        "peak_tariff_dollars_per_MWh": 72.0
      }
    ]
  },
  "comparison": {
    "cost_reduction_dollars": 0.0,
    "largest_peak_tariff_drops": [
      {
        "zone": "paint_shop",
        "baseline_peak_tariff_dollars_per_MWh": 128.0,
        "bypass_peak_tariff_dollars_per_MWh": 72.0,
        "drop_dollars_per_MWh": 56.0
      }
    ]
  }
}
```

额外要求：

- `zone_hourly_tariffs` 和 `peak_hour_by_zone` 都必须覆盖所有分区，并按 `zone` 升序排列。
- 每个 `tariffs_dollars_per_MWh` 数组都必须恰好有 24 个数，对应小时 `0` 到 `23`。
- `peak_hour` 取该分区 24 小时里价格最高的最早时段。
- `cost_reduction_dollars = baseline.total_charging_cost_dollars - bypass_cable.total_charging_cost_dollars`。
- `largest_peak_tariff_drops` 必须恰好包含 3 个分区，并按 `drop_dollars_per_MWh` 从大到小排序；若并列，按 `zone` 升序。
- `drop_dollars_per_MWh = baseline_peak_tariff_dollars_per_MWh - bypass_peak_tariff_dollars_per_MWh`，正值表示旁路电缆让该分区峰价下降。
- 所有金额都保留 2 位小数。
