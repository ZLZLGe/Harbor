你收到的是透析入科实验室的长表数据，每一行对应某个 `encounter` 的一个检验结果。不同门诊把同一检验项目写成了不同单位，原始结果里还混有科学计数法、欧洲小数写法和多余空白字符。

输入文件：

- `/root/environment/data/dialysis_intake_labs_long.csv`
- `/root/environment/data/intake_panel_reference.csv`

其中 `intake_panel_reference.csv` 给出了本次入科面板需要保留的项目、输出列名、目标单位，以及美国常用单位下的合理范围。

你的任务：

1. 只处理参考表里 `required = true` 的检验项目。
2. 清洗 `result_value_raw`：
   - 去掉首尾空白字符
   - 解析科学计数法
   - 把逗号小数写法当作十进制小数处理
3. 以 `encounter_id` 为粒度，只要某个必需项目缺行、结果为空白或无法解析，就丢弃整个 encounter。
4. 把每个必需项目统一到参考表中的目标单位。
   - 有些 `reported_unit` 很明确，可以直接按单位换算。
   - 有些 `reported_unit` 是模糊标签，例如 `local_default`，这时要结合项目本身和合理范围判断是否需要换算。
5. 把结果透视成每个 encounter 一行的宽表，保留元数据列：
   - `facility_code`
   - `patient_id`
   - `encounter_id`
   - `intake_date`
6. 输出按 `intake_date` 升序，再按 `encounter_id` 升序排序。

输出文件：

- `/root/dialysis_intake_panel_harmonized.csv`

输出列顺序必须严格为：

1. `facility_code`
2. `patient_id`
3. `encounter_id`
4. `intake_date`
5. `serum_creatinine_mg_dL`
6. `bun_mg_dL`
7. `potassium_mEq_L`
8. `bicarbonate_mEq_L`
9. `hemoglobin_g_dL`
10. `albumin_g_dL`
11. `calcium_mg_dL`
12. `phosphorus_mg_dL`

结果要求：

- 只保留完整 encounter
- 每个保留的 encounter 只出现一行
- 所有数值列都必须写成严格的 `X.XX` 格式
- 输出中不能出现空字符串、科学计数法、逗号小数或首尾空白
