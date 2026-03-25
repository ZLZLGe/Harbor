输入工作簿位于 `/root/data/training_block_experiment.xlsx`，包含 3 个工作表：

- `Roster`：运动员基本信息和分组信息。
- `BaselineTest`：训练开始前的体重、深蹲、卧推、硬拉测试。
- `BlockEnd`：训练结束后的同类测试。

请生成 `/root/results/training_block_readout.xlsx`，并且只需要包含下面 2 个工作表：

1. `AthleteReadout`
2. `Summary`

`AthleteReadout` 需要按 `athlete_id` 升序输出，每名运动员一行，列名必须严格为：

- `athlete_id`
- `athlete_name`
- `sex`
- `training_group`
- `cohort`
- `baseline_bodyweight_kg`
- `baseline_total_kg`
- `end_bodyweight_kg`
- `end_total_kg`
- `delta_total_kg`
- `delta_total_per_bw`

其中：

- `baseline_total_kg = squat_kg + bench_kg + deadlift_kg`，来自 `BaselineTest`
- `end_total_kg = squat_kg + bench_kg + deadlift_kg`，来自 `BlockEnd`
- `delta_total_kg = end_total_kg - baseline_total_kg`
- `delta_total_per_bw = delta_total_kg / baseline_bodyweight_kg`

`Summary` 需要按下面顺序输出 2 行指标：

1. `delta_total_kg`
2. `delta_total_per_bw`

列名必须严格为：

- `metric`
- `treatment_mean`
- `control_mean`
- `mean_diff`
- `ci95_lower`
- `ci95_upper`
- `cohens_d`
- `n_treatment`
- `n_control`
- `sample_size_balanced`

统计口径如下：

- 只按 `training_group` 中的 `treatment` 和 `control` 两组做汇总。
- `treatment_mean` 和 `control_mean` 是对应组内的样本均值。
- `mean_diff = treatment_mean - control_mean`
- 95% 置信区间使用正态近似：`mean_diff ± 1.96 * SE`
- `SE = sqrt(s_treatment^2 / n_treatment + s_control^2 / n_control)`，其中标准差使用样本标准差
- `cohens_d = mean_diff / pooled_sd`
- `pooled_sd = sqrt(((n_treatment - 1) * s_treatment^2 + (n_control - 1) * s_control^2) / (n_treatment + n_control - 2))`
- `sample_size_balanced` 写布尔值；当 `abs(n_treatment - n_control) <= 1` 时为 `TRUE`，否则为 `FALSE`

不要把统计结果粗暴四舍五入成整数，保留足够小数，便于复核。
