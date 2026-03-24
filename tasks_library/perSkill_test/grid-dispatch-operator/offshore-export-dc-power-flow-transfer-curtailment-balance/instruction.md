你正在支持一组海上风电场的送出控制。调度中心给出了一个当前时刻的海上汇集与送岸网络快照，你需要在海缆容量受限时决定各风场可接纳出力与弃风量。

输入文件 `offshore_snapshot.json` 给出：
- 海上节点、参考母线与送岸节点
- 各风场所在节点、可发出力，以及限电优先级（`curtailment_priority` 数字越小，越应优先保留出力）
- 各段海缆两端节点、电抗和传输上限

请计算一个满足下列条件的送出方案：
1. 总送岸功率最大
2. 每个节点满足直流潮流下的有功平衡
3. 每个风场接纳功率位于 `0` 到 `available_mw` 之间
4. 所有海缆潮流绝对值不超过各自传输上限
5. 若存在多个总送岸功率同样最大的方案，按 `curtailment_priority` 顺序优先减少高优先级风场的弃风

完成分析后，生成 `wind_export_plan.json`，结构如下：

```json
{
  "wind_farm_dispatch": [
    {
      "id": "WF-AURORA",
      "bus": 310,
      "available_MW": 105.0,
      "accepted_MW": 105.0,
      "curtailed_MW": 0.0
    }
  ],
  "summary": {
    "total_available_MW": 485.0,
    "total_accepted_MW": 314.76,
    "total_curtailed_MW": 170.24,
    "delivered_to_shore_MW": 314.76,
    "curtailment_pct": 35.1
  },
  "most_congested_cable": {
    "cable_id": "EX-510-900",
    "name": "South Export",
    "from": 510,
    "to": 900,
    "flow_MW": 165.0,
    "limit_MW": 165.0,
    "loading_pct": 100.0
  }
}
```

要求：
- `wind_farm_dispatch` 必须覆盖全部风场，且 `curtailed_MW = available_MW - accepted_MW`
- `summary.delivered_to_shore_MW` 必须等于 `summary.total_accepted_MW`
- `most_congested_cable` 需填写负载率最高的单条海缆
- 结果保留合理小数精度即可，但必须与物理约束一致
