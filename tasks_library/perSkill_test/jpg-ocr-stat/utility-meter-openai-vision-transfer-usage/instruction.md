## 任务

现场表计照片位于以下两个目录：

- `/app/workspace/field_capture/period_start`
- `/app/workspace/field_capture/period_end`

两个目录中会出现同名 PNG 文件。文件名去掉扩展名后的 basename 就是 `meter_id`，表示同一个表计在期初和期末各拍摄了一张照片。

读取每个表计数字窗中的读数，生成 `/app/workspace/meter_usage.csv`。

CSV 必须只包含以下列，顺序固定：

- `meter_id`
- `start_reading`
- `end_reading`
- `consumption`

规则：

- `meter_id` 直接使用同名文件的 basename。
- `start_reading` 和 `end_reading` 必须写成数字窗里可见的 6 位整数字符串，保留前导 `0`，不要加入空格、逗号或小数点。
- `consumption` 必须是 `end_reading - start_reading` 的十进制整数字符串，不要补前导 `0`。
- 所有表计都不存在回卷，期末读数一定不小于期初读数。
- 数据行必须按 `meter_id` 升序排序。
- 第一行必须是表头。
- 不要添加额外列、额外空行或其他输出文件。

验证会检查 CSV schema、数值格式、排序，以及最终 CSV 内容是否完全正确。
