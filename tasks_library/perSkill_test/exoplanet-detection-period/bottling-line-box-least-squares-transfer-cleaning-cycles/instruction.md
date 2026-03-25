你在 `/root/data/bottling_lines.csv` 得到了一份两条灌装线的分钟级归一化吞吐率数据，列如下：

- `line_id`
- `minute_index`
- `normalized_throughput`

两条线都已经做过基础归一化：正常生产时吞吐率大致在 `1.0` 附近，短时停机会表现为接近箱形的明显下挫。你的任务是判断哪条线存在稳定重复的清洗停机，并提取该停机的周期和持续时间。

请按下面的统一设置分析两条线：

1. 每条线独立分析，但两条线必须使用完全一致的搜索配置。
2. 停机周期搜索范围固定为 `140` 到 `260` 分钟。
3. 试探停机时长固定为 `12` 到 `36` 分钟之间的等间隔网格，至少使用 `25` 个时长样本。
4. 对每条线，读取最高功率峰对应的停机周期与停机时长。
5. 从两条线中选择最高功率峰更强的那一条，作为存在稳定清洗停机的产线。

将结果写入 `/root/output/cleaning_shutdown_report.csv`。输出必须是带表头的 CSV，并且只能包含 1 行数据。列顺序固定为：

- `line_id`
- `shutdown_period_minutes`
- `shutdown_duration_minutes`
- `downtime_fraction`

字段要求：

- `line_id` 必须是输入数据里的某个产线编号。
- `shutdown_period_minutes` 使用分钟为单位。
- `shutdown_duration_minutes` 使用分钟为单位。
- `downtime_fraction` 定义为 `shutdown_duration_minutes / shutdown_period_minutes`，表示单个清洗周期内停机时间占比。
- 3 个数值字段都保留到小数点后 `5` 位。

输出示例：

```csv
line_id,shutdown_period_minutes,shutdown_duration_minutes,downtime_fraction
LINE-00,180.00000,20.00000,0.11111
```
