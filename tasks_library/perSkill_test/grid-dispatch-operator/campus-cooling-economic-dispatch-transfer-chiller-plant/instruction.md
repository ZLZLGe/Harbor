你是一名校园区域能源中心的冷站调度工程师。当前时段内，所有冷机都已经启机待命，你需要在满足教学区总冷负荷和旋转备用要求的前提下，安排各台冷机的制冷出力，并让整站每小时电费最低。

输入数据位于 `/root/campus_cooling_snapshot.json`。其中每台冷机包含：

- `chiller_id`、`plant` 和 `reserve_priority`
- `cooling_min_RT` 与 `cooling_max_RT`
- `reserve_max_RT`
- `no_load_power_kW`
- `linear_power_kW_per_RT`
- `quadratic_power_kW_per_RT2`

每台冷机在本时段的耗电功率按下式计算：

`power_kW = no_load_power_kW + linear_power_kW_per_RT * cooling_output_RT + quadratic_power_kW_per_RT2 * cooling_output_RT^2`

总电费按：

`total_electricity_cost_dollars_per_hour = electricity_price_dollars_per_kWh * sum(power_kW)`

计算。

调度结果必须满足：

1. 总制冷出力必须精确等于 `cooling_load_RT`
2. 每台冷机的制冷出力必须位于 `[cooling_min_RT, cooling_max_RT]`
3. 每台冷机的旋转备用必须位于 `[0, reserve_max_RT]`
4. 每台冷机都满足 `cooling_output_RT + spinning_reserve_RT <= cooling_max_RT`
5. 总旋转备用不低于 `spinning_reserve_requirement_RT`
6. 如果存在多个总电费相同的最优方案，则按 `reserve_priority` 从小到大依次分配旋转备用；每台冷机先分配到其可提供上限后，再给下一台冷机

请输出 `/root/cooling_dispatch_summary.json`，结构如下：

```json
{
  "campus_id": "harbor-west-campus",
  "operating_interval": "2026-08-05T14:00:00+08:00",
  "chiller_dispatch": [
    {
      "chiller_id": "CH-N1",
      "plant": "north-plant",
      "cooling_output_RT": 640.0,
      "spinning_reserve_RT": 100.0,
      "power_draw_kW": 479.072,
      "available_capacity_RT": 760.0,
      "unused_capacity_RT": 20.0
    }
  ],
  "summary": {
    "cooling_load_RT": 2680.0,
    "scheduled_cooling_RT": 2680.0,
    "spinning_reserve_requirement_RT": 340.0,
    "scheduled_spinning_reserve_RT": 340.0,
    "total_power_kW": 2053.019,
    "total_electricity_cost_dollars_per_hour": 258.6804,
    "remaining_margin_RT": 250.0
  },
  "plant_rollup": [
    {
      "plant": "central-plant",
      "cooling_output_RT": 770.0,
      "spinning_reserve_RT": 0.0,
      "unused_capacity_RT": 100.0
    }
  ],
  "reserve_stack_order": ["CH-N2", "CH-S1", "CH-N1"]
}
```

额外要求：

- `chiller_dispatch` 必须按输入文件中的冷机顺序输出
- `plant_rollup` 按 `plant` 升序输出
- `reserve_stack_order` 只列出 `spinning_reserve_RT > 0` 的冷机，并按实际分配备用的顺序输出
- 所有数值保留到小数点后 4 位即可
