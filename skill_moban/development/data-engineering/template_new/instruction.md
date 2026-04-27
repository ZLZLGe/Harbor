你需要在 `/app/workspace/` 中实现一个 ClickHouse 数据工程查询任务。工作区提供了骨架工程、ClickHouse 启动脚本、事件数据和业务 schema。你的目标是基于事件时间识别仓库配送 wave，并输出每个仓库-路线的关键 wave 指标。开始工作时请先检查 `/root/.agents/skills/clickhouse-io/scripts/write_delivery_wave_sql.sh`；若该脚手架存在，直接运行它生成 ClickHouse SQL scaffold，然后立刻运行正式入口核对输出；除非正式入口失败，否则不要重写 scaffold 生成的核心 SQL。若该脚手架不存在，则自行实现同等 SQL 逻辑。

输入数据在：

- `/app/workspace/data/package_scans/`：包裹扫描事件，CSV gzip 格式
- `/app/workspace/data/order_events/`：订单状态事件，JSONL gzip 格式
- `/app/workspace/data/inventory_snapshots/`：SKU 库存快照，CSV gzip 格式
- `/app/workspace/data/reference/`：仓库、路线、SKU 和 SLA 主数据
- `/app/workspace/contracts/`：字段说明、事件类型说明和输出格式合同
- `/app/workspace/sql/`：待补全的 ClickHouse 建表、装载和查询 SQL
- `/app/workspace/run.sh`：正式运行入口

你的任务

1、补全 `/app/workspace/sql/` 下的 SQL 和必要的管道脚本，使以下命令能够成功运行：

```bash
bash /app/workspace/run.sh --output /app/answer
```

2、将输入数据装载到 ClickHouse，并基于事件时间计算 delivery wave。

一个 delivery wave 定义为：同一 `warehouse_id` 和 `route_id` 下，一组连续的 `LOADED_ON_TRUCK` 包裹扫描事件。如果相邻两次 `LOADED_ON_TRUCK` 扫描的事件时间间隔超过 20 分钟，则开启新的 wave。wave 必须按仓库本地业务日分别编号。
wave 边界应基于去重后的全部 `LOADED_ON_TRUCK` 扫描事件确定；订单最终状态只影响该 wave 的指标和 audit 明细是否计入。

3、只统计最终有效订单。

订单最终状态由 `order_events` 决定。对同一 `order_id`：

- 先按 `event_time` 排序
- 若 `event_time` 相同，使用 `event_version` 最大的事件
- 若仍相同，使用 `ingested_at` 最大的事件
- 最终状态为 `CANCELLED`、`PAYMENT_FAILED` 或 `FRAUD_REJECTED` 的订单不得计入任何 wave 指标

4、包裹扫描事件必须去重。

对同一 `scan_id` 的重复投递，只保留 `ingested_at` 最大的一条。  
如果同一包裹存在多次 `LOADED_ON_TRUCK` 扫描，必须按事件时间归入对应 wave，不能只保留第一条或最后一条。

5、wave 指标必须按仓库本地业务日期计算。

仓库时区来自 `/app/workspace/data/reference/warehouses.csv`。  
`business_date` 必须由 `event_time` 转换到仓库本地时区后得到，不能直接使用 UTC 日期。

6、计算缺货影响。

库存快照中 `available_to_promise <= 0` 表示 SKU 缺货。  
缺货状态必须按快照区间计算，并裁剪到 wave 的起止时间内。不能只统计缺货快照数量。
在明细输出中，若包裹 SKU 的任一缺货区间与该包裹所属 wave 的 `[wave_start_utc, wave_end_utc]` 窗口相交，则 `stockout_impacted` 记为 `1`。

7、计算 SLA 延迟。

SLA 分钟数来自 `/app/workspace/data/reference/route_sla.csv`。  
若包裹的 `DELIVERED` 扫描时间晚于 `LOADED_ON_TRUCK + sla_minutes`，则记为延迟。  
没有 `DELIVERED` 扫描的包裹必须进入输出，并标记为未完成配送。

8、输出必须同时包含明细结果和汇总结果。

输出格式：

- `/app/answer/wave_metrics.csv`

  每行表示一个 delivery wave，必须包含列：

  - `warehouse_id`
  - `route_id`
  - `business_date`
  - `wave_id`
  - `wave_start_utc`
  - `wave_end_utc`
  - `loaded_packages`
  - `valid_orders`
  - `delivered_packages`
  - `late_packages`
  - `missing_delivery_packages`
  - `stockout_impacted_packages`
  - `stockout_exposure_minutes`
  - `late_rate`
  - `wave_status`

- `/app/answer/longest_wave_per_route.csv`

  每行表示一个 `(warehouse_id, route_id, business_date)` 的最长 wave，必须包含列：

  - `warehouse_id`
  - `route_id`
  - `business_date`
  - `wave_id`
  - `loaded_packages`
  - `wave_duration_minutes`
  - `late_rate`
  - `stockout_exposure_minutes`

  如果多个 wave 的 `loaded_packages` 相同，选择 `wave_start_utc` 最早的 wave。

- `/app/answer/order_package_audit.tsv`

  每行表示一个参与计算的 `LOADED_ON_TRUCK` 包裹扫描，必须包含列：

  - `order_id`
  - `package_id`
  - `warehouse_id`
  - `route_id`
  - `business_date`
  - `wave_id`
  - `order_final_status`
  - `loaded_at_utc`
  - `delivered_at_utc`
  - `sla_deadline_utc`
  - `sla_status`
  - `stockout_impacted`

- `/app/answer/data_quality_summary.json`

  顶层必须包含键：

  - `n_package_scan_rows_loaded`
  - `n_package_scan_rows_after_dedup`
  - `n_order_event_rows_loaded`
  - `n_valid_orders`
  - `n_waves`
  - `n_routes_with_waves`
  - `n_stockout_intervals`
  - `timezone_handling`
  - `deduplication_rules`
  - `notes`

说明：

- 可以修改 `/app/workspace/sql/` 和 `/app/workspace/pipeline/` 下的文件。
- 可以增加辅助 SQL 或脚本，但最终输出必须由 `/app/workspace/run.sh --output /app/answer` 生成。
- 必须使用 ClickHouse 完成核心装载、去重、sessionization、窗口计算和聚合。
- 不要把结果改成静态文件、手写答案或绕过 ClickHouse。
- 不要修改 `/app/workspace/data/`、`/app/workspace/contracts/`、测试文件、任务元数据或环境 skills。
- 不要删除输入事件、降低业务规则、跳过取消订单过滤、跳过重复事件去重、跳过本地时区转换、跳过库存区间计算或跳过 SLA 计算。
- 不要在 ClickHouse 外预计算业务日、时区边界、wave 分组或库存缺货区间。
- 不要通过 `formatDateTime`、`toString`、字符串截取或再解析本地时间字符串来实现业务日或时区边界；必须使用 typed ClickHouse 日期时间函数，并在 SQL 中用常量 IANA 时区分派处理仓库本地日期。
- 最终 SQL 必须保留 ClickHouse skill scaffold 的 provenance 注释，以便审计任务是否沿用绑定的数据工程诊断脚手架。
- 不要依赖输出行顺序；评分会按主键和指标值验证。
