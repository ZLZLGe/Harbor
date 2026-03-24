你是一名区域供热站调度员。给定一个单时段的蒸汽站快照，你需要同时决定各锅炉和热电联产机组的蒸汽出力与热备用分配，并让总燃料成本最小。

输入数据位于 `/root/steam_station_snapshot.json`。其中每个供汽资产包含：

- `asset_id` 和 `asset_type`
- `steam_min_tph` 和 `steam_max_tph`
- `hot_reserve_max_tph`
- `hot_reserve_cost_dollars_per_tph`
- `fuel_cost_blocks`：按负荷递增顺序给出的分段燃料成本块，每个块包含 `steam_tph` 和 `marginal_cost_dollars_per_tph`

调度时必须满足：

1. 总蒸汽出力等于 `steam_demand_tph`
2. 每台资产的蒸汽出力位于 `[steam_min_tph, steam_max_tph]`
3. 每台资产的热备用位于 `[0, hot_reserve_max_tph]`
4. 每台资产都满足 `steam_output_tph + hot_reserve_tph <= steam_max_tph`
5. 总热备用不低于 `hot_reserve_requirement_tph`
6. 所有蒸汽出力和热备用都必须是 `dispatch_step_tph` 的整数倍
7. 蒸汽燃料成本按 `fuel_cost_blocks` 逐段累积，热备用成本按线性备用成本计算

请输出 `/root/steam_dispatch_report.json`，结构如下：

```json
{
  "station_id": "harbor_district_heat_evening_peak",
  "asset_dispatch": [
    {
      "asset_id": "Base-Boiler-A",
      "asset_type": "boiler",
      "steam_output_tph": 150.0,
      "hot_reserve_tph": 0.0,
      "spare_headroom_tph": 0.0
    }
  ],
  "summary": {
    "steam_demand_tph": 490.0,
    "steam_scheduled_tph": 490.0,
    "hot_reserve_requirement_tph": 95.0,
    "hot_reserve_scheduled_tph": 95.0,
    "total_fuel_cost_dollars_per_hour": 8433.5,
    "average_fuel_cost_dollars_per_ton": 17.2112
  },
  "technology_totals": [
    {
      "asset_type": "boiler",
      "steam_output_tph": 290.0,
      "hot_reserve_tph": 90.0,
      "spare_headroom_tph": 20.0
    }
  ],
  "fully_committed_assets": ["Base-Boiler-A", "Base-Boiler-B"]
}
```

额外要求：

- `asset_dispatch` 按输入文件中的资产顺序输出
- `technology_totals` 按 `asset_type` 升序输出
- `fully_committed_assets` 只包含 `spare_headroom_tph` 为 0 的资产，并按 `asset_id` 升序输出
- 所有数值保留到小数点后 4 位即可
