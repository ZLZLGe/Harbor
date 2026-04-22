你需要基于给定的 marketplace 冻结 feed 构建并发布一份日终 snapshot bundle。运行环境里已经提供了订单 CDC、履约事件、退款流水、卖家 SLA 配置、商品维表，以及本地 publish audit API。你的目标是在现有链路上产出可复核、可发布、并且能通过正式 audit 的 snapshot 交付物。

输入数据在：
- `/app/workspace/data/raw/orders_cdc.jsonl`：冻结的订单行级 CDC feed，包含晚到版本、字段漂移和不同时间格式
- `/app/workspace/data/raw/shipment_events.jsonl`：冻结的履约事件 feed，包含 shipped / delivered 等事件
- `/app/workspace/data/raw/refunds.csv`：退款流水
- `/app/workspace/data/raw/sellers.csv`：卖家维表与 SLA 时效要求
- `/app/workspace/data/raw/catalog.csv`：商品维表
- `/app/workspace/specs/`：公开的源数据契约、指标定义和发布约束
- `/app/workspace/incidents/`：历史事故记录与人工复盘结论
- 本地 publish audit API：
  - `GET http://127.0.0.1:8331/manifest`
  - `POST http://127.0.0.1:8331/publish`

你的任务
1、读取冻结的多源 feed，完成 CDC 最终版本选择、字段漂移兼容、退款合并、履约事件聚合、UTC 口径业务日期计算，以及按卖家 SLA 判定的按时发货指标。
2、构建最终 snapshot warehouse，并把正式产物写到 `/app/output/warehouse.duckdb`。至少需要产出两张表：
- `seller_daily_mart`
- `sku_fulfillment_mart`
3、通过正式链路获取 live manifest，再提交最终 publish bundle 到本地 audit API，生成：
- `/app/output/publish_bundle.json`
- `/app/output/publish_receipt.json`
4、保证同一业务键的最终结果稳定、输出结构满足发布契约、指标可复核，且结果不能依赖输入文件顺序或一次性手工整理。
5、最终交付物必须能在当前冻结主数据场景下通过 publish audit，并且在 verifier 提供的替代 fixture 下仍然保持相同的处理规则和输出语义。

输出格式：
- 生成文件：
  - `/app/output/warehouse.duckdb`
  - `/app/output/publish_bundle.json`
  - `/app/output/publish_receipt.json`
- `/app/output/warehouse.duckdb` 中必须至少包含：
  - `seller_daily_mart(snapshot_date, seller_id, seller_name, order_lines, completed_lines, cancelled_lines, shipped_lines, on_time_shipments, refunded_lines, gross_revenue_usd, refunded_revenue_usd, net_revenue_usd, avg_hours_to_ship)`
  - `sku_fulfillment_mart(snapshot_date, seller_id, sku, category, completed_lines, shipped_lines, delivered_lines, refunded_lines, net_revenue_usd, on_time_ship_rate)`
- `/app/output/publish_bundle.json` 必须是一个 JSON object，并至少包含：
  - `snapshot_id`
  - `contract_version`
  - `warehouse_path`
  - `tables`
- `/app/output/publish_receipt.json` 必须是一个 JSON object，并至少包含：
  - `request_sha256`
  - `accepted`
  - `snapshot_id`
  - `status`
  - `accepted_tables`

说明：
- 不要 hack verifier，不要针对固定卖家、固定日期、固定 SKU、固定行数、固定 hash 或测试特征做硬编码。
- 不要伪造、跳过、短路或替换真实 publish audit 链路；不要把需要 live 校验的步骤改成复制静态 bundle、手写 receipt、读取 golden 文件或直接返回成功。
- 不要删表、删指标、缩小输入范围、跳过退款、跳过 CDC 去重、跳过 SLA 判定、跳过 UTC 归一化，或通过修改业务语义规避问题。
- 不要修改隐藏服务、测试文件、冻结输入数据的业务含义或依赖配置。
- 可以增加日志、辅助脚本、局部工具代码和额外校验，但最终评分以正式输出表、正式 publish bundle、正式 receipt 和真实链路下的行为结果为准。
