你在区域调度中心值班。日前计划已经形成，但由于北送通道偏紧，运行主管要求你在不改变总负荷的前提下，做一次最小成本的实时重调度，并提交接口利用率报告。

题目输入位于 `/root/redispatch_case.json`。这是一个 MATPOWER 风格的区域网络快照，额外给出了：

- 每台机组的日前基线出力 `baseline_output_MW`
- 向上/向下重调度报价
- 向上/向下爬坡能力
- 需要监视的关键接口定义

请基于该输入求解一个满足下列条件的可行重调度：

1. 每个母线满足 DC 有功功率平衡。
2. 选择一个参考母线并固定其相角。
3. 每条线路潮流满足热稳定极限。
4. 每台机组的新出力必须同时满足：
   - 机组最小/最大出力限制
   - `baseline_output_MW - ramp_down_MW <= new_output_MW <= baseline_output_MW + ramp_up_MW`
5. 总发电量必须覆盖总负荷。
6. 目标是最小化总重调度成本：

```text
sum(
  up_bid_dollars_per_MW * max(new_output_MW - baseline_output_MW, 0)
  + down_bid_dollars_per_MW * max(baseline_output_MW - new_output_MW, 0)
)
```

然后生成 `/root/redispatch_market_report.json`，结构必须为：

```json
{
  "case_id": "regional_redispatch_alpha",
  "generator_results": [
    {
      "id": "G1",
      "bus": 1,
      "baseline_output_MW": 120.0,
      "new_output_MW": 60.0,
      "delta_MW": -60.0,
      "up_redispatch_price": 7.0,
      "down_redispatch_price": 4.0
    }
  ],
  "interfaces": [
    {
      "id": "north_south_cut",
      "flow_MW": 150.0,
      "limit_MW": 150.0,
      "loading_pct": 100.0
    }
  ],
  "totals": {
    "baseline_generation_MW": 280.0,
    "redispatched_generation_MW": 280.0,
    "load_MW": 280.0,
    "total_redispatch_cost_dollars_per_hour": 1320.0
  },
  "constrained_lines": [
    {
      "from": 3,
      "to": 4,
      "flow_MW": 150.0,
      "limit_MW": 150.0,
      "loading_pct": 100.0
    }
  ]
}
```

输出要求：

- `generator_results` 必须包含输入中全部机组，且每台机组恰好出现一次，按 `id` 升序排列。
- `interfaces` 必须包含输入中全部接口，且按 `loading_pct` 从高到低排列。
- 接口潮流按输入里 `interfaces[*].elements` 的有向求和定义计算；若元素的 `sign` 为 `-1`，表示与该线路正方向相反。
- `constrained_lines` 必须列出最终调度下所有 `loading_pct >= 85` 的线路，并按 `loading_pct` 从高到低排列。
- 所有数值保留至少 2 位小数精度即可；允许极小的浮点误差。
- 不要输出额外文件。
