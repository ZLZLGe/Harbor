你接手的是企业年度体检项目导出的批量化验表。原始数据在 `/root/environment/data/wellness_screening_labs_raw.csv`，字段目标单位与合理范围见 `/root/environment/data/wellness_screening_column_guide.csv`，不同体检供应商的默认上报单位见 `/root/environment/data/wellness_screening_vendor_unit_defaults.csv`。

这批筛查数据有几类问题：
- 不同供应商对葡萄糖、血脂、游离甲状腺素、胆红素和炎症指标使用了不同单位
- 数值格式混杂了科学计数法、逗号小数和首尾空白
- 部分员工记录缺少关键化验值，不能直接进入后续人群筛查分析
- 输出需要保留筛查批次、供应商和空腹状态，方便后续做企业人群分层

请完成以下工作：
1. 读取原始表，保留所有上下文字段，尤其是 `employee_id`、`employer_group`、`screening_cycle`、`exam_date`、`vendor_name`、`fasting_status`、`age_band`。
2. 清洗所有化验列，正确解析科学计数法、逗号小数和多余空白。
3. 删除任一化验列缺失的记录，只保留完整筛查样本。
4. 结合供应商默认单位表和字段说明，把葡萄糖、血脂、甲状腺、肝胆和炎症相关指标统一转换到字段说明要求的目标单位。
5. 所有化验列统一保留两位小数，格式必须是 `X.XX`。
6. 输出结果按 `screening_cycle`、`employee_id` 升序排列。

请把结果保存到 `/root/wellness_screening_labs_harmonized.csv`。

要求：
- 输出列顺序与输入一致
- 非数值列原样保留
- 输出中不能出现缺失值、逗号小数、科学计数法或多余空白
- 每个 `employee_id + screening_cycle` 只保留一行
- 输出结果应可直接用于企业人群筛查和患病风险分层
