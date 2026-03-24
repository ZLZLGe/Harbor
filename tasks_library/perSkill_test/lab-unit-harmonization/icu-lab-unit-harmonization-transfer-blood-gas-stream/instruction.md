你接手的是 ICU 脓毒症患者的连续血气流导出表。原始数据在 `/root/environment/data/icu_blood_gas_stream_raw.csv`，字段说明和目标单位在 `/root/environment/data/icu_blood_gas_column_guide.csv`。

这批床旁采样数据有几类问题：
- 同一指标混用了不同单位，尤其是 `pCO2`、`pO2`、`lactate`、`ionized_calcium`
- 数值格式混杂了科学计数法、逗号小数和多余空白
- 部分采样记录缺少关键化验值，不能直接进入后续酸碱分析
- 连续样本需要保留时间顺序，方便追踪病情变化

请完成以下工作：
1. 读取原始表，保留 `encounter_id`、`sample_time`、`specimen_source`、`vent_support`、`device_id` 这些非数值列。
2. 清洗所有化验列，正确解析科学计数法、逗号小数和首尾空白。
3. 删除任一化验列缺失的采样记录，只保留完整样本。
4. 结合重症血气和电解质的常见生理范围，把混合单位统一转换到字段说明表要求的目标单位。
5. 所有化验列统一保留两位小数，格式必须是 `X.XX`。
6. 输出结果按 `encounter_id`、`sample_time` 升序排列。

请把结果保存到 `/root/icu_blood_gas_harmonized.csv`。

要求：
- 输出列顺序与输入一致
- 非数值列原样保留
- 输出中不能出现缺失值、逗号小数、科学计数法或多余空白
- 每个 `encounter_id + sample_time` 只保留一行
- 输出结果应可直接用于急性酸碱状态和灌注状态分析
