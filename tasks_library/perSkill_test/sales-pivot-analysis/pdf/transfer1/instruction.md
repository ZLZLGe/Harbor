Read the multi-page store operations packet in `/root/store_packet.pdf` and create `/root/transfer1_store_kpi_rollup.csv`.

The output CSV must use this header exactly:
`region,total_orders,total_revenue,total_returns,return_rate_pct,revenue_per_labor_hour`

Requirements:
- Parse every table page in the PDF. The packet spans multiple pages and repeats the same columns.
- Treat each row as one store record with region, order count, revenue, returns, and labor hours.
- Aggregate by `region`.
- `total_orders`, `total_revenue`, and `total_returns` must be summed per region.
- `return_rate_pct` must equal `(total_returns / total_orders) * 100`, rounded to two decimal places.
- `revenue_per_labor_hour` must equal `(total_revenue / total_labor_hours)`, rounded to two decimal places.
- Sort the output rows by `region` ascending.

Save the final CSV to `/root/transfer1_store_kpi_rollup.csv`.
