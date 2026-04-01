---
name: sc-data-profiler
description: Profile raw 10x Genomics single-cell matrices from mtx/tsv or h5 input and return QC distributions for adaptive decisions. Use when the user asks for single-cell preprocessing, PBMC QC, mitochondrial ratio statistics, basic data diagnostics, or threshold selection before filtering.
---

# sc-data-profiler

Read raw 10x input without modifying it and return robust QC summary statistics for downstream adaptive decisions.

## Inputs

- Required: absolute path to raw 10x data (`--input`)
- Optional: output JSON path (`--out`)

## Output Contract

Return JSON (stdout) containing:

- `n_cells`
- `n_genes_median_per_cell`
- `mito_pct_quantiles` with `q25`, `q50`, `q90`
- `recommended_mito_cutoff_candidates`

When `--out` is provided, the same JSON is written to that path.

## Command

```bash
python scripts/profile_10x.py \
  --input /abs/path/to/10x_or_h5 \
  --out /abs/path/to/profile.json
```

## Notes

- Treat this skill as read-only on raw data.
- Use output quantiles to decide whether `max_mito_percent` should be stricter (for example 5) or looser (for example 10).
