Three outdoor sellers exported their camp-gear browse paths in different formats. The files are available in `/root/data/`:

- `alpha_market.csv`
- `bravo_market.csv`
- `charlie_market.jsonl`

Each source uses its own hierarchy wording for the same small set of camping products. Normalize the paths and produce one shared five-level taxonomy that can be used as a single reporting catalog.

Write these outputs to `/root/output/`:

1. `similar_outdoor_taxonomy_full.csv`
   - columns: `source`, `category_path`, `unified_level_1`, `unified_level_2`, `unified_level_3`, `unified_level_4`, `unified_level_5`
   - include every input record exactly once

2. `similar_outdoor_taxonomy_hierarchy.csv`
   - columns: `unified_level_1`, `unified_level_2`, `unified_level_3`, `unified_level_4`, `unified_level_5`
   - include each unique unified taxonomy path exactly once

Rules:

- keep the output taxonomy at five levels
- group semantically equivalent source paths together even when the wording differs
- use stable, reusable category names rather than copying each source verbatim
- keep the hierarchy consistent so the same product family always lands on the same unified path
