输入文件位于：

- `/root/data/turbine_sensor_logs.csv`
- `/root/data/maintenance_labels.csv`

其中：

- `turbine_sensor_logs.csv` 是分钟级传感器日志，列为 `turbine_id,event_ts,rpm,temp_c,vibration_mm_s,pressure_kpa,alarm_flag`
- `maintenance_labels.csv` 是需要产出特征的快照表，列为 `turbine_id,snapshot_ts,split,failure_within_24h`
- `split` 已经是给定的时间切分标记，只能把它原样带到输出里；做每个快照的特征时，只能使用该设备在 `snapshot_ts` 当分钟及之前的日志，不能泄漏未来分钟的信息

请生成 `/root/results/turbine_features.csv`，并且输出列名必须严格按下面顺序：

1. `turbine_id`
2. `snapshot_ts`
3. `split`
4. `failure_within_24h`
5. `rpm_mean_60m`
6. `rpm_std_60m`
7. `temp_mean_180m`
8. `temp_slope_180m`
9. `vibration_std_60m`
10. `pressure_missing_rate_180m`
11. `alarm_count_180m`

输出要求：

- 每个 `maintenance_labels.csv` 的输入行都要对应输出一行
- 输出按 `turbine_id` 升序、再按 `snapshot_ts` 升序排序
- `failure_within_24h` 保持为 0/1 整数
- 数值列保留足够小数，便于复核，不要粗暴四舍五入成整数

特征定义如下：

- 60 分钟窗口：`[snapshot_ts - 59 分钟, snapshot_ts]`，两端都包含
- 180 分钟窗口：`[snapshot_ts - 179 分钟, snapshot_ts]`，两端都包含
- 所有窗口都只看同一个 `turbine_id`
- `rpm_mean_60m`：60 分钟窗口内非空 `rpm` 的算术均值
- `rpm_std_60m`：60 分钟窗口内非空 `rpm` 的总体标准差（population standard deviation，分母用 `n`）
- `temp_mean_180m`：180 分钟窗口内非空 `temp_c` 的算术均值
- `temp_slope_180m`：在 180 分钟窗口内，对非空 `temp_c` 做一元线性回归斜率，`x` 取“距窗口起点的分钟偏移”，`y` 取 `temp_c`；斜率公式为 `sum((x - x_bar) * (y - y_bar)) / sum((x - x_bar)^2)`；如果可用点少于 2 个，则写 0
- `vibration_std_60m`：60 分钟窗口内非空 `vibration_mm_s` 的总体标准差
- `pressure_missing_rate_180m`：把 180 分钟窗口补齐成 180 个期望分钟后，`pressure_kpa` 为空或者该分钟整行日志缺失，都算缺失；缺失率 = 缺失分钟数 / 180
- `alarm_count_180m`：180 分钟窗口内 `alarm_flag` 之和

除了最终的 `/root/results/turbine_features.csv`，不要求输出其他文件。
