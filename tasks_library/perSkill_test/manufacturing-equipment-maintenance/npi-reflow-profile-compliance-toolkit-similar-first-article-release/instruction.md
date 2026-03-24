你在支持一条 NPI 产线做回流炉首件放行。请综合工艺手册、候选 run 的热电偶曲线、MES 候选记录和首件缺陷统计，输出一份唯一的放行决策文件。

可用输入文件都在 `/app/data/`:
- `npi_handbook.pdf`
- `first_article_runs.csv`
- `first_article_thermocouples.csv`
- `first_article_defects.csv`

请生成 `/app/output/first_article_release.json`，并满足以下要求：

1. 必须先从手册中提取以下规则，不能猜测：
- 预热区温度边界
- 预热最大升温斜率限制
- TAL 窗口
- 峰值温度相对 liquidus 的最小裕量
- 代表性冷点热电偶的选择规则

2. 计算规则：
- `max_preheat_ramp_c_per_s`：对每个 run 的所有热电偶，按时间排序后，在预热区内只使用两个端点都落在预热区内的相邻采样段计算斜率，取 run 级最大值。
- `representative_tc_id`：选峰值温度最低的热电偶作为代表性冷点；如果峰值相同，取字典序更小的 `tc_id`。
- `tal_s` 与 `peak_temp_c`：都基于代表性冷点热电偶计算。
- TAL 必须使用阈值穿越线性插值，不能用简单采样点计数代替。
- `thermal_status = "pass"` 仅当 ramp、TAL、peak 三项都满足手册要求。
- `quality_status = "pass"` 仅当该 run 的 critical 缺陷总数为 0，且首件 `fp_yield_pct >= 95.00`。
- `release_decision = "release"` 仅当 `thermal_status` 和 `quality_status` 都为 `pass`，否则为 `hold`。
- `failure_reasons` 只能从以下 code 中取值，并按固定顺序输出：
  1. `preheat_ramp_exceeds_limit`
  2. `tal_out_of_window`
  3. `peak_margin_not_met`
  4. `critical_defects_present`
  5. `yield_below_95`
- `total_defect_count` 为该 run 在 `first_article_defects.csv` 中所有非 `SUMMARY` 行的 `count` 之和。
- `golden_run_id` 只能在被放行的 runs 中选择，排序规则是：
  1. `fp_yield_pct` 更高优先
  2. `total_defect_count` 更低优先
  3. `max_preheat_ramp_c_per_s` 更低优先
  4. `run_id` 字典序更小优先

3. 输出要求：
- 所有浮点数保留 2 位小数。
- 所有 run 列表按 `run_id` 升序。
- 不要输出 `NaN` 或 `Infinity`，必要时使用 `null`。

请严格使用以下 JSON 结构：

```json
{
  "board_id": "NPI-000",
  "handbook_limits": {
    "preheat_temp_min_c": 0.0,
    "preheat_temp_max_c": 0.0,
    "ramp_limit_c_per_s": 0.0,
    "tal_min_s": 0.0,
    "tal_max_s": 0.0,
    "peak_margin_c": 0.0,
    "representative_tc_rule": "lowest_peak_then_smallest_tc_id"
  },
  "released_run_ids": ["FA-00"],
  "blocked_run_ids": ["FA-01"],
  "golden_run_id": "FA-00",
  "runs": [
    {
      "run_id": "FA-00",
      "representative_tc_id": "TC1",
      "max_preheat_ramp_c_per_s": 0.0,
      "tal_s": 0.0,
      "peak_temp_c": 0.0,
      "required_min_peak_c": 0.0,
      "fp_yield_pct": 0.0,
      "critical_defect_count": 0,
      "total_defect_count": 0,
      "thermal_status": "pass",
      "quality_status": "pass",
      "release_decision": "release",
      "failure_reasons": []
    }
  ]
}
```
