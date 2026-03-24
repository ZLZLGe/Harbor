你正在支持一次区域输电网的夜间检修窗口。运维团队已经把受影响线路的传输上限降额到检修期间可用值，你需要据此重新安排机组出力。

输入文件 `maintenance_window.json` 给出：
- 母线编号、负荷与参考母线
- 机组所在母线、基线出力、出力上下限与线性报价
- 线路两端、电抗，以及检修后的传输上限

请计算一个满足下列条件的最小成本重调度方案：
1. 每个母线满足直流潮流下的有功平衡
2. 所有机组出力位于各自上下限内
3. 所有线路潮流绝对值不超过检修后的传输上限
4. 参考母线相角固定为 0

完成分析后，生成 `redispatch_report.json`，结构如下：

```json
{
  "generator_dispatch": [
    {
      "id": "G-ALPHA",
      "bus": 101,
      "baseline_MW": 110.0,
      "dispatch_MW": 95.1717,
      "delta_MW": -14.8283
    }
  ],
  "bus_angles_deg": [
    {
      "bus": 101,
      "angle_deg": 0.0
    }
  ],
  "summary": {
    "total_generation_MW": 220.0,
    "total_load_MW": 220.0,
    "total_cost_usd_per_hour": 3701.39,
    "total_adjustment_MW": 80.0
  },
  "most_congested_corridor": {
    "line_id": "C-205-411",
    "name": "Valley Tie",
    "from": 205,
    "to": 411,
    "flow_MW": 28.0,
    "limit_MW": 28.0,
    "loading_pct": 100.0
  }
}
```

要求：
- `generator_dispatch` 必须覆盖全部机组，`delta_MW = dispatch_MW - baseline_MW`
- `bus_angles_deg` 必须覆盖全部母线，按角度参考母线为 0 的结果填写
- `summary.total_generation_MW` 必须等于总负荷
- `most_congested_corridor` 需填写检修后负载率最高的单条线路
