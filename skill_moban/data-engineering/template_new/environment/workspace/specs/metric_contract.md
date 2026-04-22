# Metric Contract

正式发布需要构建两张表：

## seller_daily_mart

- 粒度：`snapshot_date + seller_id`
- 输出字段：
  - `snapshot_date`
  - `seller_id`
  - `seller_name`
  - `order_lines`
  - `completed_lines`
  - `cancelled_lines`
  - `shipped_lines`
  - `on_time_shipments`
  - `refunded_lines`
  - `gross_revenue_usd`
  - `refunded_revenue_usd`
  - `net_revenue_usd`
  - `avg_hours_to_ship`

## sku_fulfillment_mart

- 粒度：`snapshot_date + seller_id + sku`
- 输出字段：
  - `snapshot_date`
  - `seller_id`
  - `sku`
  - `category`
  - `completed_lines`
  - `shipped_lines`
  - `delivered_lines`
  - `refunded_lines`
  - `net_revenue_usd`
  - `on_time_ship_rate`

## 业务约束

- `snapshot_date` 以统一时间基准下的业务日期计算。
- 收入、退款和净收入之间必须自洽。
- 取消订单不能被当成已完成收入计入口径。
- 指标必须来源于最终快照版本，而不是任意中间版本。
- 字段顺序、字段名和数值语义必须稳定，便于下游 publish audit 复核。
