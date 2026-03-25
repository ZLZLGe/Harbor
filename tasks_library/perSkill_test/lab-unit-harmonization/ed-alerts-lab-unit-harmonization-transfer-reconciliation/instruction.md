你收到的是急诊危急检验对账事件流。每一行是一条单独的危急检验结果事件，原始结果里混有科学计数法、逗号小数、首尾空白，而且不同来源会把同一检验项目写成不同单位。

输入文件：

- `/root/environment/data/ed_alert_stream.jsonl`
- `/root/environment/data/critical_test_reference.csv`

其中：

- `critical_test_reference.csv` 给出了本次对账只关心的检验项目、标准检验名称、目标单位、目标输出顺序，以及目标单位下的合理范围。
- `ed_alert_stream.jsonl` 里只有 `test_code` 出现在参考表中的记录才需要纳入对账；其他检验项目直接忽略，不要写进输出，也不要计入排除列表。

你的任务：

1. 读取事件流，只处理参考表中列出的目标检验项目。
2. 清洗 `result_raw`：
   - 去掉首尾空白字符
   - 解析科学计数法
   - 把逗号小数写法当作十进制小数处理
3. 对目标检验项目统一单位到参考表中的 `target_unit`。
   - 如果 `reported_unit` 已经是目标单位，或与目标单位数值等价，则直接保留数值。
   - `reported_unit` 可能是模糊标签 `ed_default`，这时要结合该检验项目在参考表中的合理范围判断当前值是否已经是目标单位；如果不是，再尝试按该项目常见替代单位换算到目标单位。
4. 只要目标记录缺少以下任一关键字段，就不要进入标准化结果，而是记入所属 encounter 的 `excluded_records`：
   - `record_id`
   - `encounter_id`
   - `test_code`
   - `arrival_time`
   - `result_raw`
   对应原因字段写成 `missing_<field_name>`，例如 `missing_result_raw`、`missing_arrival_time`。
5. 以 `encounter_id` 为粒度输出 JSON 报告。每个 encounter 需要列出：
   - `encounter_id`
   - `patient_id`
   - `arrival_time`
   - `had_unit_conversion`
   - `standardized_results`
   - `excluded_records`
6. `had_unit_conversion` 的含义是：该 encounter 中至少有一条进入 `standardized_results` 的记录发生过单位换算。
7. 所有进入 `standardized_results` 的 `standard_value` 必须写成严格的 `X.XX` 字符串格式。

输出文件：

- `/root/ed_alert_lab_reconciliation.json`

输出 JSON 的顶层结构必须严格为：

```json
{
  "report_id": "ed-critical-lab-reconciliation",
  "target_tests": [
    {
      "test_code": "...",
      "standard_name": "...",
      "standard_unit": "..."
    }
  ],
  "encounters": [
    {
      "encounter_id": "...",
      "patient_id": "...",
      "arrival_time": "...",
      "had_unit_conversion": true,
      "standardized_results": [
        {
          "record_id": "...",
          "test_code": "...",
          "standard_name": "...",
          "standard_value": "X.XX",
          "standard_unit": "...",
          "converted": true
        }
      ],
      "excluded_records": [
        {
          "record_id": "...",
          "test_code": "...",
          "reason": "missing_result_raw"
        }
      ]
    }
  ]
}
```

排序要求：

- `target_tests` 按参考表里的 `display_order` 升序
- `encounters` 先按 `arrival_time` 升序，再按 `encounter_id` 升序
- 每个 encounter 内的 `standardized_results` 按参考表里的 `display_order` 升序，再按 `record_id` 升序
- 每个 encounter 内的 `excluded_records` 按 `record_id` 升序

结果要求：

- 只输出至少出现过一条目标检验记录的 encounter
- `standardized_results` 中不能出现空字符串、科学计数法、逗号小数或首尾空白
- 非目标检验项目完全忽略，不要出现在 `standardized_results` 或 `excluded_records`
