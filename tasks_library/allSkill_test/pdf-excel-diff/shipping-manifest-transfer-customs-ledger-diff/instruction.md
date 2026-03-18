You are reconciling an archived export manifest packet against the current customs ledger.

Inputs:
- Archived PDF packet: `/root/export_manifest_packet.pdf`
- Current Excel ledger: `/root/customs_ledger.xlsx`

Workbook details:
- The workbook contains a single sheet named `CurrentLedger`.
- Columns are:
  - `manifest_id`
  - `line_no`
  - `item_code`
  - `destination_port`
  - `carton_count`
  - `gross_weight_kg`
  - `declared_value_usd`

Comparison rules:
1. Treat the PDF as the older archived state and the Excel workbook as the current state.
2. Use the joint key (`manifest_id`, `line_no`) to match rows.
3. Report rows that appear in the PDF but do not appear in the workbook as missing line items.
4. Ignore rows that exist only in the workbook.
5. For matched rows, compare only these fields:
   - `destination_port`
   - `carton_count`
   - `gross_weight_kg`
   - `declared_value_usd`

Write `/root/shipping_manifest_variances.json` in this format:

```json
{
  "missing_line_items": [
    {
      "manifest_id": "MNF-1002",
      "line_no": 3
    }
  ],
  "changed_line_items": [
    {
      "manifest_id": "MNF-1001",
      "line_no": 2,
      "field": "destination_port",
      "old_value": "Long Beach",
      "new_value": "Los Angeles"
    }
  ]
}
```

Requirements:
- Output `line_no` and `carton_count` as integers.
- Output `gross_weight_kg` and `declared_value_usd` as numbers.
- Output `destination_port` as a string.
- Sort `missing_line_items` by `manifest_id`, then `line_no`.
- Sort `changed_line_items` by `manifest_id`, then `line_no`, then `field`.
