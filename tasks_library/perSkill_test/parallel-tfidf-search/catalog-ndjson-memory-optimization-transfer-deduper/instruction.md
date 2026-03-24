# Transfer: Memory-Efficient Catalog Deduper

In `/root/workspace/`, there is a baseline product-catalog normalizer for supplier feed snapshots. It produces exact canonical catalog records, but it reads the whole NDJSON file into memory, keeps every normalized row alive, and duplicates many repeated strings and sparse attribute objects.

Write your solution in `/root/workspace/catalog_deduper_solution.py`.

You must implement these functions:

1. `dedupe_catalog(catalog_path)`
2. `write_canonical_catalog(catalog_path, output_path)`

The input is an NDJSON file where each line is one raw catalog record. Helper code in `/root/workspace/catalog_common.py`, `/root/workspace/catalog_baseline.py`, and `/root/workspace/catalog_factory.py` defines the schema, normalization helpers, exact baseline behavior, and the synthetic catalog generator used by the verifier.

Canonicalization rules:

- Deduplicate records by normalized uppercase `sku`.
- `display_name` is the longest cleaned title in the group; ties use lexicographically smaller text.
- `brand` is the lexicographically smallest non-empty cleaned brand in the group.
- `category_path` is the longest normalized category path in the group; ties use lexicographically smaller tuples.
- `price_cents`, `currency`, and `availability` come from the latest record in the group, ordered by `updated_at` and then input line order.
- For each normalized attribute key, keep the latest non-empty normalized value using the same ordering.
- `tags` are the sorted unique normalized tags gathered from every record in the group.
- Output records must be sorted by ascending `sku`.

Requirements:

- Preserve the exact canonical records, counts, ordering, and NDJSON serialization produced by the baseline for the same file.
- Process the catalog directly from `catalog_path` without materializing the full parsed NDJSON and all per-record normalized objects at once.
- `dedupe_catalog` must return a `CatalogBuildResult` whose `.records` items are `CanonicalCatalogRecord` objects from `catalog_common.py`.
- `write_canonical_catalog` must write canonical NDJSON using the field order produced by `canonical_record_to_dict` in `catalog_common.py`.
- The verifier checks a provided fixture catalog, randomized generated catalogs, and a peak-memory benchmark on a much larger synthetic feed.

Do not modify the helper modules or the provided fixture assets.
