You are auditing changes between an archived supplier price list PDF and the current CSV procurement list.

Inputs:
- Archived PDF: `/root/vendor_price_archive.pdf`
- Current CSV: `/root/current_procurement_list.csv`

Tasks:
1. Extract the archived product table from the PDF.
2. Compare it with the current CSV by `sku`.
3. Identify:
   - `discontinued_skus`: SKUs that exist in the PDF but no longer exist in the CSV
   - `changed_items`: retained SKUs whose `unit_price` or `min_order_qty` changed

Write the result to `/root/vendor_diff_report.json` in this format:

```json
{
  "discontinued_skus": ["VND-1004", "VND-1009"],
  "changed_items": [
    {
      "sku": "VND-1002",
      "field": "unit_price",
      "old_value": 1.25,
      "new_value": 1.4
    }
  ]
}
```

Requirements:
- Ignore SKUs that appear only in the current CSV.
- Only report changes for `unit_price` and `min_order_qty`.
- Output numeric values as numbers.
- Sort `discontinued_skus` in ascending SKU order.
- Sort `changed_items` by `sku`, then by `field`.
- Use the exact top-level keys and write valid JSON.
