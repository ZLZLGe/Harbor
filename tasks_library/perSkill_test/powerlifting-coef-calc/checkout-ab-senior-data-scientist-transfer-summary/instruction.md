输入文件位于 `/root/data/checkout_funnel_events.csv`。它是一个事件级 CSV，每行代表一次结账漏斗事件，列为：

- `session_id`
- `variant`
- `event_name`
- `event_ts`
- `device`
- `order_value_usd`

其中：

- `variant` 只会取 `control` 或 `treatment`
- 同一个 `session_id` 只属于一个 `variant`
- 只要某个 session 至少出现一次 `purchase` 事件，就视为该 session 转化

请生成 `/root/results/checkout_experiment_summary.json`，输出一个 JSON 对象，并按下面结构提供结果：

```json
{
  "groups": {
    "control": {
      "sessions": 0,
      "purchases": 0,
      "conversion_rate": 0.0
    },
    "treatment": {
      "sessions": 0,
      "purchases": 0,
      "conversion_rate": 0.0
    }
  },
  "comparison": {
    "absolute_lift": 0.0,
    "relative_lift": 0.0,
    "p_value": 0.0
  },
  "srm_check": {
    "expected_proportions": {
      "control": 0.5,
      "treatment": 0.5
    },
    "observed_sessions": {
      "control": 0,
      "treatment": 0
    },
    "chi_square_stat": 0.0,
    "p_value": 0.0,
    "flagged": false
  },
  "decision": {
    "recommend_launch": false,
    "blocking_checks": []
  }
}
```

统计口径如下：

- `groups.control.sessions` 和 `groups.treatment.sessions`：各组唯一 `session_id` 数量
- `groups.<variant>.purchases`：各组发生过 `purchase` 的唯一 `session_id` 数量
- `groups.<variant>.conversion_rate = purchases / sessions`
- `comparison.absolute_lift = treatment.conversion_rate - control.conversion_rate`
- `comparison.relative_lift = absolute_lift / control.conversion_rate`
- `comparison.p_value` 使用双侧两比例 z 检验，采用 pooled standard error：
  - `p_pool = (x_treatment + x_control) / (n_treatment + n_control)`
  - `SE = sqrt(p_pool * (1 - p_pool) * (1 / n_treatment + 1 / n_control))`
  - `z = (p_treatment - p_control) / SE`
  - `p_value` 为该 `z` 的双侧正态检验 p 值
- `srm_check` 以唯一 session 数做 50/50 分流检查：
  - `expected_proportions.control = 0.5`
  - `expected_proportions.treatment = 0.5`
  - `observed_sessions` 写各组唯一 session 数
  - `chi_square_stat = sum((observed - expected)^2 / expected)`，其中每组 `expected = total_sessions * 0.5`
  - `srm_check.p_value` 使用自由度为 1 的卡方检验 p 值
  - `srm_check.flagged = (srm_check.p_value < 0.01)`

`decision` 的规则必须严格按下面顺序生成：

1. 如果 `comparison.absolute_lift <= 0`，向 `blocking_checks` 追加 `"non_positive_lift"`
2. 如果 `comparison.p_value >= 0.05`，向 `blocking_checks` 追加 `"not_significant"`
3. 如果 `srm_check.flagged` 为 `true`，向 `blocking_checks` 追加 `"srm_flagged"`
4. 当且仅当 `blocking_checks` 为空数组时，`recommend_launch` 为 `true`，否则为 `false`

不要把结果粗暴四舍五入成整数，保留足够小数以便复核。JSON 里的布尔值必须是真正的布尔值。
