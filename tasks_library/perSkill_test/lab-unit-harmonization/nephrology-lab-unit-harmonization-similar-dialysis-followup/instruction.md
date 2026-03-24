你接手的是一家透析连锁机构导出的月度随访化验表。原始文件在 `/root/environment/data/dialysis_followup_labs_raw.csv`，列解释和目标单位见 `/root/environment/data/dialysis_followup_column_guide.csv`。

这份随访表存在几类问题：
- 部分随访行有缺失值，不能直接进入完整队列
- 数值格式混杂了科学计数法、逗号小数和多余空白
- 肌酐、尿酸、血红蛋白、总钙、白蛋白、铝等字段混用了不同单位
- 同一列的小数位数不一致

请完成以下工作：
1. 读取原始表，保留 `patient_code`、`followup_month`、`clinic_code`、`access_type` 这些非数值列。
2. 对其余化验列做清洗：去掉空白，正确解析科学计数法和逗号小数。
3. 删除任一化验列缺失的随访行，只保留完整随访队列。
4. 结合透析随访的常见生理范围，把混合单位统一转换为列说明表要求的常规单位。
5. 所有化验列统一保留两位小数，格式必须是 `X.XX`。

请把结果保存到 `/root/dialysis_followup_labs_harmonized.csv`。

要求：
- 输出列顺序与输入一致
- 非数值列原样保留
- 输出中不能出现缺失值、逗号小数、科学计数法或多余空白
- 每个 `patient_code + followup_month` 只保留一行
