You are reconciling an archived equipment inspection registry against the current registry workbook.

Inputs:
- Archived PDF report: `/root/equipment_inspection_report.pdf`
- Current Excel workbook: `/root/equipment_registry.xlsx`

The PDF contains the older inspection snapshot. The workbook contains the current registry. Each equipment record uses these columns:
- `asset_tag`
- `equipment_name`
- `location`
- `next_inspection_date`
- `service_vendor`
- `risk_level`
- `inspection_interval_days`

Your task:

1. Extract the equipment table from the archived PDF.
2. Compare it with the current Excel workbook.
3. Identify:
   - `retired_equipment`: asset tags present in the archived PDF but missing from the current workbook
   - `updated_records`: for asset tags present in both sources, emit one entry per changed field for these tracked fields only:
     - `next_inspection_date`
     - `service_vendor`
     - `risk_level`
     - `inspection_interval_days`

Write the result to `/root/equipment_registry_changes.json` in this format:

```json
{
  "retired_equipment": ["EQ-1004", "EQ-1008"],
  "updated_records": [
    {
      "asset_tag": "EQ-1002",
      "field": "next_inspection_date",
      "old_value": "2025-09-15",
      "new_value": "2025-10-15"
    }
  ]
}
```

Requirements:
- Treat the PDF as the old state and the Excel workbook as the new state.
- Ignore equipment that exists only in the current workbook.
- Normalize all `next_inspection_date` values to `YYYY-MM-DD` before comparing and before writing them to the output.
- Output `inspection_interval_days` values as integers.
- Output `service_vendor` and `risk_level` values as strings.
- Sort `retired_equipment` in ascending `asset_tag` order.
- Sort `updated_records` by `asset_tag`, then by `field`.
