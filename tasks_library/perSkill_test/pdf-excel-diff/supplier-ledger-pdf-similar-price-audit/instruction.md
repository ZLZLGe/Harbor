You are helping a procurement team audit supplier pricing changes.

An archived supplier ledger is stored as a PDF at `/root/supplier_ledger_archive.pdf`. A newer CSV export is stored at `/root/supplier_prices_current.csv`.

Your task is to:

1. Extract the pricing table from the archived PDF.
2. Compare it with the current CSV export.
3. Write `/root/supplier_price_diff.json` with:
   - `discontinued_skus`: SKUs that exist in the archived PDF but do not exist in the current CSV
   - `updated_products`: one entry for every changed field on SKUs that still exist in both files

Use this exact JSON structure:

```json
{
  "discontinued_skus": ["SUP-1007", "SUP-1018"],
  "updated_products": [
    {
      "sku": "SUP-1003",
      "field": "UnitPrice",
      "old_value": 4.85,
      "new_value": 5.10
    }
  ]
}
```

Notes:
- The PDF contains the older version of the supplier data.
- The CSV contains the newer version of the supplier data.
- The table columns are `SKU`, `Description`, `Category`, `Unit`, `Currency`, `UnitPrice`, `LeadDays`, and `MOQ`.
- `UnitPrice` must be written as a number.
- `LeadDays` and `MOQ` must be written as integers.
- Text fields must be written as strings.
- Sort `discontinued_skus` in ascending SKU order.
- Sort `updated_products` by `sku`, then by `field`.
- Do not include unchanged products or extra keys.
