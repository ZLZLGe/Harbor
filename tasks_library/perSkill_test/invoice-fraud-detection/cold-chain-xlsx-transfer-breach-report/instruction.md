你需要分析一份冷链运输监控工作簿，并输出批次级 CSV 违规报告。

输入文件：
- `/root/cold_chain_monitor_book`
  - `Route SLA`：每条线路的温控阈值、累计超限阈值、恢复时限、最大允许读数间隔和装车宽限期
  - `Trips`：运输任务与线路信息
  - `Batch Map`：货运批次、所属运输任务、绑定传感器、装车完成时间和交接时间
  - `Sensor Log`：传感器温度时序日志

请生成 `/root/cold_chain_breaches.csv`，并满足以下要求：

1. 输出必须是 UTF-8 编码的 CSV，表头和列顺序严格为：
   - `batch_id`
   - `route_id`
   - `breach_minutes`
   - `breach_type`
2. 对每个批次，先通过 `Batch Map.trip_id` 关联 `Trips.route_id`，再读取对应线路在 `Route SLA` 中的规则。
3. 监控窗口定义为：
   - `window_start = load_end_ts + loading_grace_min`
   - `window_end = handoff_ts`
   - 所有时间都按工作簿内给出的本地时间处理，不需要做时区换算。
4. 同一传感器的日志必须按 `reading_ts` 升序解释。每条读数只在以下区间内有效：
   - 从该条 `reading_ts` 开始
   - 到下一条同传感器读数的 `reading_ts` 为止
   - 但最长不能超过该线路的 `max_gap_min`
   - 也就是说，每条读数的有效截止时间是 `min(next_reading_ts, reading_ts + max_gap_min)`
5. 计算覆盖区间时，允许使用监控窗口开始之前的最后一条同传感器读数，只要它的有效区间延伸进监控窗口。
6. 如果监控窗口内存在任意未被有效读数覆盖的分钟数，则该批次视为不可判定：
   - 只输出一行 `breach_type = sensor_missing`
   - `breach_minutes` 写监控窗口内未被覆盖的总分钟数
   - 一旦命中 `sensor_missing`，该批次不要再输出其他类别
7. 对于没有缺测的批次，再判定温度违规。温度上限使用 `Route SLA.temp_limit_c`，只有 `temperature_c > temp_limit_c` 才算超限。
8. `cumulative_over_limit`：
   - 将监控窗口内所有超限区间的分钟数求和
   - 若总和严格大于 `cumulative_breach_limit_min`，输出一行
   - `breach_minutes` 写该批次的总超限分钟数
9. `recovery_timeout`：
   - 连续超限区间构成一个超限片段；只有出现 `temperature_c <= temp_limit_c` 的有效区间时，才视为恢复
   - 若任一超限片段的时长严格大于 `recovery_limit_min`，输出一行
   - 如果同一批次有多个超时片段，只输出一行，`breach_minutes` 写最长超时片段分钟数
10. 同一批次可以同时输出 `cumulative_over_limit` 和 `recovery_timeout` 两行；除此之外不要输出重复行。
11. 输出排序要求：
   - 先按 `route_id` 升序
   - 再按 `batch_id` 升序
   - 再按 `breach_type` 升序
12. `breach_minutes` 必须写成整数分钟；不要输出额外列，也不要包含未违规批次。
