You are reconciling an archived vendor pricebook against the current workbook.

Inputs:
- Archived PDF: `/root/vendor_catalog_archive.pdf`
- Current Excel workbook: `/root/vendor_pricebook_current.xlsx`

The PDF contains the older version of the catalog. The workbook contains the current version. Each catalog record uses these columns:
- `SKU`
- `ItemName`
- `Category`
- `UnitPrice`
- `Currency`
- `PackSize`
- `LeadTimeDays`

Your task:

1. Extract the archived product table from the PDF.
2. Compare it with the current Excel workbook.
3. Identify:
   - `discontinued_skus`: SKUs present in the archived PDF but missing from the current workbook
   - `modified_skus`: for SKUs present in both sources, emit one entry per changed field with `sku`, `field`, `old_value`, and `new_value`

Write the result to `/root/vendor_catalog_diff.json` in this format:

```json
{
  "discontinued_skus": ["SKU-1004", "SKU-1009"],
  "modified_skus": [
    {
      "sku": "SKU-1002",
      "field": "UnitPrice",
      "old_value": 33.0,
      "new_value": 34.5
    }
  ]
}
```

Requirements:
- Treat the PDF as the old state and the Excel workbook as the new state.
- Ignore SKUs that exist only in the current workbook.
- Output numeric fields (`UnitPrice`, `PackSize`, `LeadTimeDays`) as numbers.
- Output text fields as strings.
- Sort `discontinued_skus` in ascending SKU order.
- Sort `modified_skus` by `sku`, then by `field`.
