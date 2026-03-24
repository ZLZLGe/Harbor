你在支持一条环氧灌封固化炉做批次处置。请综合固化规范、批次日志和埋入式热电偶曲线，输出一份唯一的批次处置结果。

可用输入文件都在 `/app/data/`:
- `cure_spec.pdf`
- `batch_log.csv`
- `embedded_tc_curves.csv`

请生成 `/app/output/cure_batch_disposition.csv`，并满足以下要求：

1. 必须先从固化规范中提取以下规则，不能猜测：
- 升温斜率的温度区间
- 最大允许升温斜率
- 有效保温时间的温度下限、温度上限和合格窗口
- 峰值超冲的定义与放行上限
- 批内均温性的定义与上限
- `release`、`hold`、`rebake` 的处置逻辑
- `reason_codes` 的固定输出顺序
- `rebake_profile` 的固定编码

2. 计算规则：
- `max_warmup_ramp_c_per_min`：对每个热电偶按时间排序后，只对两个端点都落在升温温区内的相邻采样段计算斜率，单位为 `C/min`，取 batch 级最大值。
- `hold_limiting_tc_id`：对每个热电偶计算有效保温时间，取最短者；若并列，取字典序更小的 `tc_id`。
- `effective_hold_s`：只统计温度位于有效保温温区内的持续时间，必须对上下边界都使用线性插值，不能用简单采样点计数代替。
- `hottest_tc_id`：取峰值温度最高的热电偶；若并列，取字典序更小的 `tc_id`。
- `coolest_peak_tc_id`：取峰值温度最低的热电偶；若并列，取字典序更小的 `tc_id`。
- `peak_overshoot_c = max(0, hottest_peak_temp_c - target_peak_c)`，其中 `target_peak_c` 来自 `batch_log.csv`。
- `peak_uniformity_c = hottest_peak_temp_c - coolest_peak_temp_c`。
- `disposition = "release"` 仅当升温斜率、有效保温时间、峰值超冲、批内均温性全部合格，且 `door_open_alarm = 0`。
- `disposition = "rebake"` 仅当以下条件同时满足：
  - 除了 `effective_hold_short` 之外没有其他热历程失败原因；
  - `rebake_allowed = "yes"`；
  - `rebake_count = 0`；
  - `door_open_alarm = 0`；
  - 峰值超冲满足 rebake 上限；
  - 批内均温性满足规范上限。
- 其他情况一律输出 `disposition = "hold"`。
- `reason_codes` 只能从以下 code 中取值，并按固定顺序用 `|` 连接；如果没有失败原因，输出空字符串：
  1. `warmup_ramp_high`
  2. `effective_hold_short`
  3. `effective_hold_long`
  4. `peak_overshoot_high`
  5. `uniformity_exceeds_limit`
  6. `door_open_alarm`
  7. `rebake_not_allowed`
- 对于 `effective_hold_short` 但最终不能 `rebake` 的 batch，必须补充 `rebake_not_allowed`。
- `rebake_profile` 只有在 `disposition = "rebake"` 时填写规范中的固定编码，否则输出空字符串。

3. 输出要求：
- 输出必须是 CSV，列顺序固定为：
  - `batch_id`
  - `product_code`
  - `hold_limiting_tc_id`
  - `hottest_tc_id`
  - `coolest_peak_tc_id`
  - `max_warmup_ramp_c_per_min`
  - `effective_hold_s`
  - `peak_overshoot_c`
  - `peak_uniformity_c`
  - `disposition`
  - `reason_codes`
  - `rebake_profile`
- 所有浮点数保留 2 位小数。
- 所有行按 `batch_id` 升序。
- 不要输出 `NaN` 或 `Infinity`。
