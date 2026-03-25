你在海上风电外送值班台负责处理海缆降额后的弃风方案。当前各汇集站的可发出力已经给定，允许通过弃风降低注入；你的目标是在满足线性潮流与海缆限额的前提下，求出总弃风最小的保留出力方案，并提交关键海缆载荷结果。

题目输入位于 `/root/offshore_export_case.json`，包含：

- `buses`：母线列表，其中 `type = "slack"` 的母线为陆上换流站，相角固定为 0
- `stations`：各海上汇集站的母线位置、`available_MW` 与 `priority_weight`
- `cables`：海缆参数，方向固定为 `from -> to`
- `report_cable_ids`：输出中必须展示的关键海缆列表
- `critical_threshold_pct`：关键海缆判定阈值
- `objective_total_curtailment_weight`：总弃风优先级系数

请按以下规则生成 `/root/offshore_curtailment_plan.json`：

1. 对每个汇集站选择 `retained_MW`，并满足 `0 <= retained_MW <= available_MW`。
2. `curtailed_MW = available_MW - retained_MW`。
3. 除陆上换流站外，不存在额外负荷或固定注入；每个汇集站母线的净注入就是 `retained_MW / baseMVA`。
4. 陆上换流站是唯一参考母线，其相角固定为 0，并吸收全部保留出力。
5. 海缆潮流按输入方向计算：

```text
flow_MW = baseMVA * (theta_from - theta_to) / x_pu
```

6. 每条海缆都必须满足 `abs(flow_MW) <= limit_MW`。
7. 载荷率定义为：

```text
loading_pct = abs(flow_MW) / limit_MW * 100
```

8. 优化目标是最小化：

```text
optimization_score =
  objective_total_curtailment_weight * total_curtailment_MW
  + weighted_curtailment_score
```

其中：

```text
total_curtailment_MW = sum(curtailed_MW)
weighted_curtailment_score = sum(priority_weight * curtailed_MW)
```

`objective_total_curtailment_weight` 足够大，表示先最小化总弃风量，再用 `priority_weight` 做同等总弃风下的稳定排序。

输出文件结构必须为：

```json
{
  "case_id": "offshore_export_delta",
  "station_plans": [
    {
      "id": "OS1",
      "name": "北屿汇集站",
      "bus": 311,
      "available_MW": 140.0,
      "retained_MW": 0.0,
      "curtailed_MW": 140.0,
      "priority_weight": 6.0
    }
  ],
  "key_cable_results": [
    {
      "id": "EXP_N",
      "name": "北登陆外送海缆",
      "from": 311,
      "to": 901,
      "kind": "export",
      "flow_MW": 155.0,
      "limit_MW": 155.0,
      "loading_pct": 100.0
    }
  ],
  "critical_cables": [
    {
      "id": "EXP_N",
      "name": "北登陆外送海缆",
      "kind": "export",
      "loading_pct": 100.0
    }
  ],
  "totals": {
    "available_MW": 510.0,
    "retained_MW": 316.45,
    "total_curtailment_MW": 193.55,
    "weighted_curtailment_score": 1107.77,
    "optimization_score": 1936648.68
  }
}
```

输出要求：

- `station_plans` 必须覆盖输入中的全部汇集站，并严格保持输入顺序。
- `key_cable_results` 必须覆盖 `report_cable_ids` 中的全部海缆，并严格保持 `report_cable_ids` 的顺序。
- `critical_cables` 只保留 `loading_pct >= critical_threshold_pct` 的海缆，按 `loading_pct` 从高到低排序；若并列，按 `id` 升序。
- `totals.available_MW`、`totals.retained_MW` 和 `totals.total_curtailment_MW` 必须分别等于各汇集站对应量的求和。
- 所有数值保留至少 2 位小数精度即可，允许极小浮点误差。
- 不要输出额外文件。
