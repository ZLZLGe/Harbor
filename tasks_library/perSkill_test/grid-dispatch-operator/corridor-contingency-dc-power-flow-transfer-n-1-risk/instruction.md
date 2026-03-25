你在送端风电外送走廊做运维风险审计。调度已经给出一组固定基态注入，不允许重调度；你的任务是评估若干单回线停运后的线路越限风险，并给出场景排序。

题目输入位于 `/root/corridor_case.json`。其中包含：

- 母线列表：`generation_MW`、`load_MW` 与参考母线类型
- 线路列表：编号、方向、标幺电抗 `x_pu`、热稳定限额 `limit_MW`
- 监视接口：由若干线路按有向符号求和定义
- 单回线停运候选场景：每个场景只切除一条线路

请按以下规则完成分析：

1. 基态净注入固定为 `generation_MW - load_MW`，各场景都不允许改变。
2. 对每个停运场景，移除 `outaged_branch_id` 对应线路，仅对剩余在运线路求解 DC 潮流。
3. 参考母线为输入中 `type = "slack"` 的母线，并固定其相角为 0。
4. 线路潮流方向定义为输入里 `from -> to`；潮流计算结果可为正或负。
5. `most_loaded_line.loading_pct = abs(flow_MW) / limit_MW * 100`。
6. `max_over_limit_pct = max(most_loaded_line.loading_pct - 100, 0)`。
7. 先计算一次基态接口载荷率；之后每个停运场景的 `affected_interfaces` 仅保留满足 `abs(post_loading_pct - base_loading_pct) >= 5.0` 的接口。
8. 如果某个接口元素引用了已停运线路，则该元素在该场景下按 0 MW 计入接口潮流。

生成 `/root/contingency_risk_rankings.json`，结构必须为：

```json
{
  "case_id": "wind_export_corridor_beta",
  "scenario_results": [
    {
      "scenario_id": "OUT_L3",
      "outaged_branch_id": "L3",
      "most_loaded_line": {
        "id": "L4",
        "from": 309,
        "to": 518,
        "flow_MW": 195.0,
        "limit_MW": 93.0,
        "loading_pct": 209.68,
        "over_limit_pct": 109.68
      },
      "max_over_limit_pct": 109.68,
      "affected_interfaces": [
        {
          "id": "metro_ring",
          "flow_MW": 259.51,
          "limit_MW": 120.0,
          "loading_pct": 216.26,
          "delta_loading_pct": 121.94
        }
      ]
    }
  ],
  "top_3_riskiest_scenarios": [
    {
      "scenario_id": "OUT_L3",
      "outaged_branch_id": "L3",
      "max_over_limit_pct": 109.68,
      "most_loaded_line_id": "L4"
    }
  ]
}
```

输出要求：

- `scenario_results` 必须覆盖输入中的全部停运场景，并严格保持输入顺序。
- `most_loaded_line` 必须来自该场景仍在运的线路；若 `loading_pct` 并列，取 `id` 字典序更小的线路。
- `affected_interfaces` 按 `abs(delta_loading_pct)` 从高到低排序；若并列，按 `id` 升序。
- `top_3_riskiest_scenarios` 按 `max_over_limit_pct` 从高到低排序；若并列，按 `scenario_id` 升序；只保留前三名。
- 所有数值保留至少 2 位小数精度即可，允许极小浮点误差。
- 不要输出额外文件。
