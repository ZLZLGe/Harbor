这个 transfer 任务要求你把同一类时序清洗思路迁移到光伏阵列功率比值序列上。

你会在 `/root/data/pv_array_ratio.csv` 得到一段一分钟采样的光伏阵列功率比值序列。文件包含这些列：

- `timestamp`: ISO 8601 时间戳，采样间隔名义上为 1 分钟
- `power_ratio`: 实测功率与基准功率的比值
- `maintenance_flag`: 维护标记，`0` 表示正常，非零表示该分钟不可用
- `module_temp_c`: 组件温度，单位摄氏度
- `irradiance_index`: 已归一化的辐照度指标

这段序列里混有维护分钟、逆变器造成的单点尖峰，以及温度驱动的缓慢漂移。你的任务是按下面的固定规则完成清洗，并把关键汇总写入 `/root/pv_drift_report.json`。

处理规则：

1. 先丢弃所有 `maintenance_flag != 0` 的样本。
2. 仅在第 1 步保留下来的序列上，按原始时间顺序计算 `power_ratio` 的居中滚动中位数，窗口大小为 `21`，并使用 `min_periods=11`。
3. 将绝对残差 `abs(power_ratio - rolling_median_21)` 大于 `0.035` 的点视为逆变器尖峰并移除；不要插值、不要重采样。
4. 在第 3 步剩余的序列上，再计算 `power_ratio` 的居中滚动中位数，窗口大小为 `121`，并使用 `min_periods=61`，把这个序列作为慢漂移基线。窗口边缘产生的空值要用最近的可用基线值向两端填充。
5. 令 `clean_ratio = power_ratio / drift_baseline`，然后再整体除以 `clean_ratio` 自身的中位数，使最终 `clean_ratio` 的中位数恰好为 `1.0`。

统计定义：

1. `preclean_dispersion_mad`：第 1 步保留下来的原始 `power_ratio` 相对其自身中位数的中位绝对偏差。
2. `cleaned_dispersion_mad`：最终 `clean_ratio` 相对 `1.0` 的中位绝对偏差。
3. `cleaned_std`：最终 `clean_ratio` 的总体标准差，使用 `ddof=0`。
4. `stability_improvement_ratio`：`preclean_dispersion_mad / cleaned_dispersion_mad`。
5. “稳定发电分钟”定义为 `abs(clean_ratio - 1.0) <= 0.006`。
6. “最长稳定发电区间”定义为：在最终保留样本中，满足上条条件且相邻两个样本时间差正好为 `60` 秒的最长连续序列；若并列，取最早开始的那个区间。
7. `duration_minutes` 直接写该最长区间的样本数；`max_abs_deviation` 定义为该区间内 `abs(clean_ratio - 1.0)` 的最大值。

输出 JSON 必须是一个对象，并至少包含这些字段：

- `source_file`: 字符串，写成 `/root/data/pv_array_ratio.csv`
- `removed_points`: 对象，至少包含 `maintenance`、`spikes`、`total`
- `cleaned_points`: 整数
- `preclean_dispersion_mad`: 数值
- `cleaned_dispersion_mad`: 数值
- `cleaned_std`: 数值
- `stability_improvement_ratio`: 数值
- `longest_stable_generation_interval`: 对象

其中 `longest_stable_generation_interval` 至少包含：

- `start_timestamp`: 字符串
- `end_timestamp`: 字符串
- `duration_minutes`: 整数
- `n_points`: 整数
- `mean_clean_ratio`: 数值
- `max_abs_deviation`: 数值

额外约束：

1. `removed_points.total` 必须等于 `removed_points.maintenance + removed_points.spikes`。
2. `cleaned_points` 必须等于输入总点数减去 `removed_points.total`。
3. `duration_minutes` 必须与 `n_points` 一致。
4. 所有统计值都必须直接由同一份最终清洗结果计算得到。
5. 验证会检查你的报告是否能从输入数据按以上规则复算出来，并确认清洗后离散度明显下降。
