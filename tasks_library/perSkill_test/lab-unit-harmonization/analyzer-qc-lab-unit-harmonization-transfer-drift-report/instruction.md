你收到的是医院检验科多台分析仪的质控测量日志。不同分析仪会把同一质控项目写成不同单位，原始结果里还混有科学计数法、逗号小数、首尾空白，以及少量无法直接使用的记录。

输入文件：

- `/root/environment/data/qc_measurement_log.csv`
- `/root/environment/data/qc_target_ranges.csv`

其中：

- `qc_target_ranges.csv` 给出了每个 `test_code + qc_level` 的标准名称、目标单位、目标区间、用于判断模糊单位的合理范围、常见替代单位列表，以及输出排序顺序。
- `qc_measurement_log.csv` 是原始质控运行日志。只有 `test_code + qc_level` 出现在参考表中的记录才需要处理；其他项目直接忽略。

你的任务：

1. 只处理参考表中存在的 `test_code + qc_level` 组合。
2. 清洗 `result_raw`：
   - 去掉首尾空白字符
   - 解析科学计数法
   - 把逗号小数写法当作十进制小数处理
3. 对每条可用记录，把结果统一到参考表中的 `target_unit`。
   - 如果 `reported_unit` 已经等于目标单位，或与目标单位数值等价，则直接保留数值。
   - 如果 `reported_unit = instrument_default`，先判断当前值是否已经落在参考表给出的 `plausible_low` 到 `plausible_high` 范围内；如果是，就把它视为目标单位。
   - 如果 `reported_unit = instrument_default` 但当前值不在上述范围内，就按照参考表 `alternate_units` 列中给出的顺序，依次尝试把它当作替代单位换算到目标单位；只要换算后的值落入 `plausible_low` 到 `plausible_high` 范围，就采用这次换算结果。
4. 下面两类记录不要进入均值计算，但要计入对应分组的 `excluded_run_count`：
   - `run_id` 为空白
   - `result_raw` 为空白，或清洗后仍无法解析成数值
5. 以 `run_date + analyzer_id + test_code + qc_level` 为粒度聚合，生成漂移报告。
   - `included_run_count`：进入均值计算的记录数
   - `converted_run_count`：进入均值计算且发生了单位换算的记录数
   - `excluded_run_count`：同一分组内因为第 4 条原因被排除的记录数
   - `standardized_mean`：该分组所有可用标准化结果的算术平均值
   - `target_midpoint`：`(target_low + target_high) / 2`
   - `relative_target_bias_pct`：先把 `standardized_mean` 按两位小数写出，再用这个两位小数值计算 `((standardized_mean - target_midpoint) / target_midpoint) * 100`
   - `out_of_control`：基于写入报告的 `standardized_mean` 判断；当它严格小于 `target_low` 或严格大于 `target_high` 时为 `true`，否则为 `false`
6. 只输出 `included_run_count >= 1` 的分组。
7. 所有小数字段都必须写成严格的 `X.XX` 格式。

输出文件：

- `/root/analyzer_qc_drift_report.csv`

输出列顺序必须严格为：

1. `report_date`
2. `analyzer_id`
3. `test_code`
4. `qc_level`
5. `standard_name`
6. `target_unit`
7. `included_run_count`
8. `converted_run_count`
9. `excluded_run_count`
10. `standardized_mean`
11. `target_midpoint`
12. `relative_target_bias_pct`
13. `out_of_control`

排序要求：

- 先按 `report_date` 升序
- 再按 `analyzer_id` 升序
- 再按参考表里的 `display_order` 升序
- 最后按 `qc_level` 升序

结果要求：

- 输出中不能包含未在参考表列出的项目
- `standardized_mean`、`target_midpoint`、`relative_target_bias_pct` 不能出现空字符串、科学计数法、逗号小数或首尾空白
- `included_run_count`、`converted_run_count`、`excluded_run_count` 必须是十进制整数字符串或整数列
