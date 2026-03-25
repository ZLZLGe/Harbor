你收到的是一份国际多中心 CKD 药物试验筛选期实验室原始上报数据。不同站点把同一检验项目混合写成美国常用单位和 SI 单位，原始结果里还夹杂科学计数法、逗号小数和首尾空白。

输入文件：

- `/root/environment/data/trial_screening_site_labs.csv`
- `/root/environment/data/registry_lab_spec.csv`

其中 `registry_lab_spec.csv` 给出了注册库允许接收的检验项目、标准检验名称、目标 SI 单位，以及判断模糊单位时可参考的 SI 合理范围。

你的任务：

1. 只保留同时满足以下条件的结果行：
   - `result_status = FINAL`
   - `analyte_code` 出现在 `registry_lab_spec.csv` 中
2. 清洗 `result_raw`：
   - 去掉首尾空白字符
   - 解析科学计数法
   - 把逗号小数写法当作十进制小数处理
3. 如果 `result_raw` 为空白、无法解析，或者标准化后仍无法落入该项目在参考表给出的 SI 合理范围，就丢弃该行。
4. 把保留下来的结果统一成参考表中的目标 SI 单位。
   - 明确写出美国常用单位时，按项目对应换算方向转成 SI。
   - 明确写出目标 SI 单位时，直接保留。
   - `reported_unit` 可能是模糊标签 `site_default` 或 `legacy_panel`，这时要结合项目的 SI 合理范围判断原值是否已经是 SI；如果不是，再尝试按该项目的美国常用单位换算到 SI。
5. 输出列顺序必须严格为：
   1. `study_id`
   2. `country_code`
   3. `site_code`
   4. `subject_id`
   5. `screening_visit`
   6. `collection_date`
   7. `specimen_id`
   8. `registry_test_code`
   9. `registry_test_name`
   10. `standard_value`
   11. `standard_unit`
6. 输出按以下顺序排序：
   - 先按 `collection_date` 升序
   - 再按 `site_code` 升序
   - 再按 `subject_id` 升序
   - 最后按 `specimen_id` 升序

输出文件：

- `/root/trial_screening_labs_si.csv`

结果要求：

- 每个保留的 `specimen_id` 只出现一行
- `standard_value` 必须写成严格的 `X.XX` 格式
- `standard_unit` 必须全部等于参考表中的目标 SI 单位
- 输出中不能出现空字符串、科学计数法、逗号小数或首尾空白
