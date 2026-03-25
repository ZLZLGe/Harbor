# Transfer: Streaming XML Catalog Inventory

In `/root/workspace/` there is a baseline script `catalog_inventory_baseline.py` and a deterministic fixture generator `catalog_fixture.py`.

The baseline reads an entire product catalog XML tree into memory before it computes category totals. That approach preserves the required output, but it uses too much memory once the catalog gets large. You need to write a replacement at `/root/workspace/catalog_inventory_solution.py`.

Your script must support this command line interface:

```bash
python /root/workspace/catalog_inventory_solution.py \
  --input /path/to/catalog.xml \
  --output /path/to/catalog_summary.json
```

Input format:

- The XML root is `<catalog ...>` and always has a `currency` attribute.
- Each product is one direct child `<product sku="..."> ... </product>` under the root.
- Every `<product>` contains these child elements:
  - `<category id="..." name="..." />`
  - `<inventory quantity="..." />`
  - `<pricing current="..." />`
- A product may also contain extra tags that are irrelevant for the summary and must be ignored.

Output contract:

1. Write a JSON object to `--output` with this exact top-level structure:

```json
{
  "catalog": {
    "currency": "USD",
    "category_count": 0,
    "total_sku_count": 0
  },
  "categories": [
    {
      "category_id": "appliances",
      "category_name": "Appliances",
      "sku_count": 0,
      "inventory_total": 0,
      "price_min": "0.00",
      "price_max": "0.00"
    }
  ]
}
```

2. `catalog.currency` must equal the root `currency` attribute from the input file.
3. `catalog.category_count` must equal the number of distinct category IDs in the input.
4. `catalog.total_sku_count` must equal the number of `<product>` elements processed.
5. `categories` must be sorted by `category_id` ascending.
6. For each category row:
   - `sku_count`: number of products in that category
   - `inventory_total`: sum of every `inventory.quantity` in that category
   - `price_min`: lowest `pricing.current` in that category, formatted as a string with exactly two decimal places
   - `price_max`: highest `pricing.current` in that category, formatted as a string with exactly two decimal places
7. Do not add extra top-level keys or extra keys inside each category row.
8. The result must match the baseline semantics on the provided sample input and on verifier-generated fixtures.
9. On the large verifier fixture, peak RSS must stay at or below `160 MB`.
10. You may use `/tmp` for temporary files if needed, but the only required deliverable is `/root/workspace/catalog_inventory_solution.py`.

Available assets:

- `/root/workspace/catalog_inventory_baseline.py`
- `/root/workspace/catalog_fixture.py`
- `/root/workspace/sample_catalog.xml`

The verifier will run your script on multiple catalog fixtures and check both correctness and memory usage.
