You are preparing the follow-up package for the pasilla treatment comparison.

Input data is in `/root/environment/data/`:
- `counts/raw_counts.tsv`: gene-level raw read counts for all samples
- `metadata/sample_metadata.tsv`: sample metadata, including treatment labels and technical factors
- `gene_panel/priority_panel.tsv`: genes that must appear in the follow-up review table
- `gene_panel/analysis_config.json`: comparison settings, model factors, filtering rule, and reporting threshold

Your task:
1. Produce the primary treated-versus-untreated analysis using the factors listed in `analysis_config.json`.
2. Produce a condition-only sensitivity rerun for the same comparison on the same retained samples and genes.
3. Deliver the result table, normalized counts, panel review table, and summary JSON.

Output:
- `/root/pasilla_differential_expression.csv`
  - UTF-8 CSV
  - Columns, in this order:
    `gene_id,baseMean,log2FoldChange,lfcSE,stat,pvalue,padj,direction`
  - Sort rows by `padj` ascending, then `log2FoldChange` descending, then `gene_id` ascending; place missing `padj` values last
  - `direction` must be one of: `up`, `down`, `ns`
  - Set `direction` from the sign of `log2FoldChange`: positive = `up`, negative = `down`, zero or missing = `ns`
  - Include every gene retained by the primary analysis

- `/root/pasilla_normalized_counts.tsv`
  - Tab-separated table
  - Rows must be retained samples
  - Columns must be retained genes

- `/root/pasilla_panel_review.tsv`
  - Tab-separated table
  - Include every gene from `priority_panel.tsv`
  - Columns, in this order:
    `gene_id,review_bucket,report_priority,note,release_baseMean,release_log2FoldChange,release_padj,reference_log2FoldChange,reference_padj,release_significant,reference_significant,stabilized_abs_log2FoldChange,follow_up_action,manual_review_rank,final_direction`
  - Sort rows by `report_priority`, then `review_bucket`, then `gene_id`
  - Set `release_significant` and `reference_significant` from the adjusted p-value threshold in `analysis_config.json`
  - `stabilized_abs_log2FoldChange` must be non-negative and must come from the primary analysis
  - `follow_up_action` must be one of:
    `ready_for_release`, `release_with_caution`, `needs_manual_review`, `no_follow_up`
  - Set `follow_up_action` with these rules:
    both significant = `ready_for_release`
    release significant only = `release_with_caution`
    sensitivity rerun significant only = `needs_manual_review`
    neither significant = `no_follow_up`
  - `manual_review_rank` must be blank for rows outside `needs_manual_review`
  - For `needs_manual_review` rows, assign consecutive ranks starting from `1`, ordered by `stabilized_abs_log2FoldChange` descending, then `gene_id` ascending
  - `final_direction` must mirror the primary analysis direction for the same gene; use `ns` only when no release direction is available

- `/root/pasilla_summary.json`
  - JSON object
  - Include:
    `comparison`: string, must be `treated vs untreated`
    `release_design_factors`: array, use the factor order from `analysis_config.json`
    `sensitivity_design`: string, must be `~condition`
    `sample_count`
    `tested_gene_count`
    `significant_up_count`
    `significant_down_count`
    `release_panel_gene_count`
    `manual_review_gene_count`
    `release_panel_genes`: array of panel genes with `release_significant = true`
    `manual_review_shortlist`: array of panel genes with `follow_up_action = needs_manual_review`, in `manual_review_rank` order
    `top_up_genes`: the first `report_top_n` significant `up` genes from the sorted primary result table
    `top_down_genes`: the first `report_top_n` significant `down` genes from the sorted primary result table
    `follow_up_action_counts`: object with all four keys
      `ready_for_release`
      `release_with_caution`
      `needs_manual_review`
      `no_follow_up`

Notes:
- Use the provided raw counts as the analysis input.
- Keep sample IDs aligned between the count matrix and the metadata, and preserve the sample order from `sample_metadata.tsv` in the normalized counts output and in the model input.
- Use the same retained sample set and retained gene set for both analyses.
- Treat the model factors used in the design as categorical metadata fields.
- Apply the reporting threshold from `analysis_config.json`.
- Use the primary analysis when you compute `stabilized_abs_log2FoldChange` for manual review ranking.
- Do not modify files under `/root/environment/data/`.
- Do not download additional datasets or use external online analysis services.
- Only write the output files listed above.
- Do not alter installed skill files.
