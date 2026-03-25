Three merchandising planners exported home-organization browse paths that need to be folded into one search-routing taxonomy. The files are in `/root/data/`:

- `planner_a.csv`
- `planner_b.txt`
- `planner_c.jsonl`

The three planners use different wording for the same landing-page routes. Build one shared three-level taxonomy and write the outputs to `/root/output/`.

Required outputs:

1. `transfer3_search_routes.tsv`
   - tab-separated file
   - columns: `source`, `source_path`, `unified_top`, `unified_mid`, `unified_leaf`, `route_slug`
   - include every source record exactly once

2. `transfer3_route_catalog.md`
   - markdown document listing each unique route once
   - include the route slug and its unified taxonomy path

Rules:

- equivalent browse paths must map to the same route slug
- the route slug should be stable and URL-safe
- the markdown catalog must cover the exact set of unique routes found in the TSV
