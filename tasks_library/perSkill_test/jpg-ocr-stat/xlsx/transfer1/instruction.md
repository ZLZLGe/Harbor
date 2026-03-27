## Task Description

`/app/workspace/stock.csv` contains current warehouse inventory:

- `sku`
- `on_hand`
- `reorder_point`
- `unit_cost`

Create `/app/workspace/transfer1.xlsx` with one sheet `plan` and exactly these columns:

- `sku`
- `on_hand`
- `reorder_point`
- `order_qty`
- `reorder_cost`

Rules:

1. `order_qty = max(reorder_point - on_hand, 0)`.
2. `reorder_cost = order_qty * unit_cost`, formatted with exactly two decimals.
3. Sort rows by `order_qty` descending; break ties by `sku` ascending.
4. First row must be header. No extra sheets, columns, or rows.
