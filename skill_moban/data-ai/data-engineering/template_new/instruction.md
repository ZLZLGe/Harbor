你在 `/app/workspace/` 接手一个本地 ClickHouse 数据链路。它原本应该把两个月的 NYC Yellow Taxi 行程数据和 Taxi Zone 维表装载到容器内的本地 ClickHouse，并产出给运营团队使用的日级与月级分析结果；现在现有链路会产出错误结果，部分下游对象缺失或口径不一致。

输入数据在 `/app/workspace/data/`：
- `yellow_tripdata_2023-01.parquet`
- `yellow_tripdata_2023-02.parquet`
- `taxi_zone_lookup.csv`
- `trip_record_user_guide.pdf`
- `data_dictionary_trip_records_yellow.pdf`

已提供的运行入口和相关代码在 `/app/workspace/`：
- `run_pipeline.sh`：本地重建链路的统一入口，路径和文件名不要修改
- `pipeline/`
- `sql/`

你的任务
1. 修复现有本地 ClickHouse 装载与转换链路，使 `run_pipeline.sh` 能够基于上述两个 Parquet 文件和 zone lookup 维表重建完整结果。保留现有目录结构、运行入口和真实数据链路，不要把 ClickHouse 替换成其他实现。
2. 让链路在执行完成后产出并保持以下结果可用：
   - ClickHouse 数据库 `analytics` 中的表 `daily_borough_metrics`
   - ClickHouse 数据库 `analytics` 中的表 `top_zone_routes`
   - 文件 `/app/workspace/output/summary.json`
3. 满足以下业务口径：
   - 两个月的 Parquet 输入都必须参与计算，不能只处理单月数据。
   - `daily_borough_metrics` 必须按 `service_date` 和 `pickup_borough` 聚合，并至少包含 `trip_count`、`gross_revenue`、`avg_trip_miles`、`avg_tip_pct`、`airport_trip_count`。
   - `airport_trip_count` 统计 pickup 或 dropoff 落在 airport service zone 的有效行程数。
   - `top_zone_routes` 必须按自然月分别产出每月前 20 条高收入路线排名，并至少包含 `service_month`、`pickup_zone`、`dropoff_zone`、`trip_count`、`gross_revenue`、`avg_duration_minutes`、`revenue_rank`。
   - 聚合结果只应包含满足业务有效性的行程；明显无效、关键字段缺失或无法完成 zone 映射的记录不应进入最终统计。
   - `avg_tip_pct` 只基于可计算小费比例的记录。

输出
- `/app/workspace/output/summary.json` 必须是合法的 UTF-8 JSON，并至少包含以下字段：
  - `source_months`
  - `raw_trip_rows`
  - `accepted_trip_rows`
  - `daily_borough_metrics_rows`
  - `top_zone_routes_rows`
- `source_months` 必须按顺序写成 `["2023-01", "2023-02"]`。
- `run_pipeline.sh` 结束后，上述两个 ClickHouse 表必须可直接查询，且 `summary.json` 必须由当前源数据重新生成。

说明
- 不要删除必需的下游表、输出文件或任一输入数据来规避问题。
- 不要把真实链路替换成只用 pandas、SQLite、静态 CSV/JSON 导出或其他绕开 ClickHouse 的方案。
- 不要硬编码最终结果，不要提交预先算好的答案文件，不要通过修改源数据来规避错误。
- 不要通过创建空表、写入占位结果或跳过实际装载与转换步骤来规避问题。
- 可以在现有工作区内补充辅助脚本或 SQL，但要保留既有入口路径与交付物名称。
