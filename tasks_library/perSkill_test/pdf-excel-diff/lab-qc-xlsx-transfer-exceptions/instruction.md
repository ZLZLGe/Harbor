你在协助实验室质量团队复核一份多工作表的质控工作簿。

输入文件：
- `/root/lab_qc_runbook.xlsx`

与本任务有关的工作表只有这 5 个：
- `Batch Summary`
- `Plate Map`
- `Readings`
- `QC Limits`
- `Specimen Intake`

这些工作表的标题行不在同一行，但正式表头一定包含下面规则里引用到的列名。

请生成 `/root/lab_qc_exceptions.json`，格式如下：

```json
{
  "failed_control_wells": [
    {
      "batch_id": "B-101",
      "well": "A01",
      "control_code": "NEG_CTRL",
      "signal": 0.22
    }
  ],
  "duplicate_sample_ids": ["S-2001", "S-4001"],
  "high_variance_batches": [
    {
      "batch_id": "B-100",
      "duplicate_group": "DG-100-A",
      "sample_id": "S-1002",
      "variance": 6.25,
      "variance_limit": 4.0
    }
  ]
}
```

判定规则：

1. `failed_control_wells`
- 从 `Plate Map` 中筛选 `entry_type = CONTROL` 的记录。
- 使用 `batch_id + well` 到 `Readings` 中找到对应的 `signal`。
- 使用 `control_code` 到 `QC Limits` 中找到该对照的 `min_signal` 和 `max_signal`。
- 只要 `signal` 不在闭区间 `[min_signal, max_signal]` 内，就输出一条失败记录。
- 每条记录只包含 `batch_id`、`well`、`control_code`、`signal` 这 4 个字段。

2. `duplicate_sample_ids`
- 只基于 `Specimen Intake` 工作表判断。
- 对 `sample_id` 先去掉首尾空白。
- 忽略清洗后为空的值。
- 把出现次数大于 1 的编号去重后输出。
- 比较时大小写敏感。

3. `high_variance_batches`
- 只基于 `Plate Map` 中 `entry_type = DUPLICATE` 且 `duplicate_group` 非空的记录判断。
- 同一个 `batch_id` 内，每个 `duplicate_group` 恰好对应 2 个孔位。
- 取这 2 个孔位在 `Readings` 中的 `signal`，按总体方差计算：
  - `variance = ((x1 - mean)^2 + (x2 - mean)^2) / 2`
- 使用 `batch_id` 到 `Batch Summary` 中找到该批次的 `duplicate_variance_limit`。
- 当 `variance` 严格大于 `duplicate_variance_limit` 时，输出一条记录。
- 每条记录只包含 `batch_id`、`duplicate_group`、`sample_id`、`variance`、`variance_limit` 这 5 个字段。

通用要求：
- `signal`、`variance`、`variance_limit` 必须输出为 JSON 数值，不要写成字符串。
- `variance` 保留两位小数。
- `failed_control_wells` 按 `batch_id`、`well` 升序排序。
- `duplicate_sample_ids` 按字典序升序排序。
- `high_variance_batches` 按 `batch_id`、`duplicate_group` 升序排序。
- 输出必须是合法 JSON，且只包含题目要求的顶层字段。
