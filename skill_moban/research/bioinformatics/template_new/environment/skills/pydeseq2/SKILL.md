---
name: pydeseq2_bulk_rnaseq
description: Diagnose and repair bulk RNA-seq differential expression pipelines that should use PyDESeq2 with explicit technical-factor adjustment and panel reporting.
---

# PyDESeq2 for Bulk RNA-seq Differential Expression

Use this skill when the task involves bulk RNA-seq count matrices, treatment-vs-control differential expression, technical-factor adjustment, or outputs that should look like DESeq2-style results.

## When This Skill Is Useful

- The input is a raw integer count matrix, not TPM/FPKM/log-transformed values.
- Sample metadata contains both a biological condition and one or more technical factors such as batch, library type, donor, or replicate block.
- The task asks for `log2FoldChange`, `pvalue`, `padj`, normalized counts, or a report derived from a DESeq2-like workflow.
- A broken pipeline appears to run but likely uses the wrong design formula, wrong contrast direction, or the wrong data orientation.

## Core Reminders

1. PyDESeq2 expects counts in `samples x genes` shape.
2. Keep only raw non-negative integer counts as model input.
3. Filter out very low-count genes before fitting. A common rule is total count across samples `>= 10`.
4. Put technical factors before the biological variable of interest in the design, for example:

```python
design = "~type + condition"
```

5. For a treated-vs-control comparison, make the contrast explicit:

```python
contrast = ["condition", "treated", "untreated"]
```

6. Use the adjusted p-value (`padj`) for final significance calls.
7. If the task also requires normalized counts, export `dds.layers["normed_counts"]`.
8. If there is a downstream panel summary, build it from the corrected DE results rather than from a stale or separately ranked gene list.
9. If the task asks for a panel audit, compare a baseline single-factor fit against the corrected multi-factor fit and classify genes as stable, rescued, or nuisance-sensitive.

## Fast Probe Script

This skill ships a helper probe at:

`/root/.codex/skills/35__pydeseq2/scripts/run_deseq2_panel_analysis.py`

It can quickly reconstruct a verifier-compatible delivery bundle:

- `differential_expression.csv`
- `significant_genes.tsv`
- `normalized_counts.tsv`
- `panel_diagnostics.tsv`
- `report.json`

using the configured multi-factor design plus a baseline single-factor comparison.

Typical usage:

```bash
python /root/.codex/skills/35__pydeseq2/scripts/run_deseq2_panel_analysis.py \
  --config /root/environment/data/gene_panel/analysis_config.json \
  --output /tmp/pasilla_probe
```

Then inspect `/tmp/pasilla_probe/panel_diagnostics.tsv` and `/tmp/pasilla_probe/report.json` to verify:

- `stable_treatment_signal`
- `rescued_after_adjustment`
- `nuisance_sensitive_drop`
- `baseline_base_mean` and `corrected_base_mean` are both present
- `contrast.corrected_design_formula` and `contrast.baseline_design_formula` are both present
- `significant_genes.tsv` includes `is_panel_gene`
- `report.json.panel_summary` includes `diagnostic_status_counts`, `n_reportable_panel_genes`, `top_panel_genes`, and exact key `reportable_genes`

## Output Contract Reminders

If you choose not to reuse the helper script and instead patch the pipeline manually, keep these exact task-level schema details:

- `significant_genes.tsv` should be built from the corrected significant set, not only the panel subset.
- `significant_genes.tsv` must carry `is_panel_gene` so panel hits can be sliced back out during verification.
- `panel_diagnostics.tsv` should include both baseline and corrected statistics plus `final_direction` and `diagnosis_note`.
- `report.json.panel_summary.reportable_genes` must be named exactly `reportable_genes`.
- Do not rename that key to variants like `reportable_panel_genes`, even if the meaning feels clearer.

## Minimal Workflow

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

counts = pd.read_csv("raw_counts.tsv", sep="\t", index_col=0).T
metadata = pd.read_csv("sample_metadata.tsv", sep="\t").set_index("sample_id")
counts = counts.loc[metadata.index]

genes_to_keep = counts.columns[counts.sum(axis=0) >= 10]
counts = counts[genes_to_keep]

inference = DefaultInference(n_cpus=1)
dds = DeseqDataSet(
    counts=counts,
    metadata=metadata,
    design="~type + condition",
    refit_cooks=True,
    inference=inference,
)
dds.deseq2()

ds = DeseqStats(
    dds,
    contrast=["condition", "treated", "untreated"],
    alpha=0.1,
    inference=inference,
)
ds.summary()
results = ds.results_df
```

## Checks That Often Catch the Real Bug

- If the top hits look dominated by a technical factor, inspect whether the design omitted that factor.
- If effect directions seem reversed, verify the contrast order and reference level.
- If the report and significant-gene table disagree, make them both derive from the same corrected result table.
- If a helper script exists, do not stop at an exploratory panel table; emit the full final bundle expected by the task contract.
- If normalized counts use the wrong sample order, check that metadata index and count-matrix sample order were aligned before fitting.

## Task-Specific Hint Pattern

When a task ships both a configuration file and sample metadata, prefer reconstructing the corrected design formula from the configuration, then compare it against a baseline formula built from the primary contrast factor alone.
