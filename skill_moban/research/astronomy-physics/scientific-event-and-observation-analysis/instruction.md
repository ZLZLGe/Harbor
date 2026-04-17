# 任务说明（观测事件模板）

你需要对观测事件日志做聚合统计，输出稳定、可程序化判定的汇总表。

## 输入
- 输入文件：`/app/workspace/input/events.csv`
- 字段定义：
  - `event_id`：事件编号
  - `event_type`：事件类型
  - `city`：地点
  - `severity`：严重级别（整数）
  - `start_time`、`end_time`：ISO 时间字符串（`YYYY-MM-DDTHH:MM:SS`）

## 输出
- 输出文件：`/app/workspace/output/event_summary.csv`
- 必须包含且仅包含以下字段（顺序固定）：
  - `event_type`
  - `event_count`
  - `avg_duration_hours`
  - `max_severity`
  - `latest_start_time`

## 处理规则
1. 按 `event_type` 分组聚合。
2. `event_count` 为每组记录数。
3. 单条持续时长 `duration_hours = end_time - start_time`（单位小时）。
4. `avg_duration_hours` 为组内平均时长，保留 3 位小数。
5. `max_severity` 为组内最大严重级别。
6. `latest_start_time` 为组内最大的 `start_time`（字典序与时间序一致）。
7. 输出按 `event_type` 升序排序。

## 禁止事项
- 不允许丢弃合法输入记录。
- 不允许改写输入文件。
- 不允许使用主观评分或非程序化规则。
