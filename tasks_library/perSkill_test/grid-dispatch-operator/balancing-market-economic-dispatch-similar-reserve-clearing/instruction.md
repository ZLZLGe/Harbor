你是一名区域平衡市场调度员。给定一个单区域、无输电网络约束的市场快照，你需要同时决定各机组的能量出清和旋转备用出清，并让总报价成本最小。

输入数据位于 `/root/balancing_market_snapshot.json`。其中每台机组包含：

- `p_min_MW` 和 `p_max_MW`
- `reserve_max_MW`
- `reserve_offer_dollars_per_MW`
- `energy_blocks`：按报价顺序给出的分段能量报价块，每个块包含 `mw` 和 `price`

你生成的结果必须满足：

1. 总能量出清等于系统负荷 `load_MW`
2. 每台机组的能量出清位于 `[p_min_MW, p_max_MW]`
3. 每台机组的备用出清位于 `[0, reserve_max_MW]`
4. 每台机组都满足 `energy_MW + reserve_MW <= p_max_MW`
5. 总备用出清不低于 `reserve_requirement_MW`
6. 能量成本按 `energy_blocks` 逐段累积，备用成本按线性报价计算

请输出 `/root/balancing_market_report.json`，结构如下：

```json
{
  "market_id": "north_delta_balancing_hour_2026-07-15T18:00:00Z",
  "unit_dispatch": [
    {
      "unit_id": "Aster-CCGT-1",
      "energy_MW": 60.0,
      "reserve_MW": 0.0,
      "headroom_MW": 120.0,
      "p_max_MW": 180.0
    }
  ],
  "totals": {
    "load_MW": 360.0,
    "energy_cleared_MW": 360.0,
    "reserve_requirement_MW": 140.0,
    "reserve_cleared_MW": 140.0,
    "total_cost_dollars_per_hour": 5964.0
  },
  "marginal_tight_units": [
    {
      "unit_id": "Cascade-Hydro-3",
      "binding_reason": "energy_plus_reserve_hits_pmax",
      "headroom_MW": 0.0
    }
  ],
  "uncommitted_capacity_MW": 210.0
}
```

额外要求：

- `unit_dispatch` 按输入文件中的机组顺序输出
- `marginal_tight_units` 只包含 `headroom_MW` 为 0 的机组，并按 `unit_id` 升序排序
- 所有数值保留到小数点后 4 位即可
