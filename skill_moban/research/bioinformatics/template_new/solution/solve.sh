#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
from pathlib import Path

import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

RUNTIME_ROOT = Path(os.environ.get("TASK_RUNTIME_ROOT", "/root"))

CONFIG_PATH = RUNTIME_ROOT / "environment/data/gene_panel/analysis_config.json"

RESULT_PATH = RUNTIME_ROOT / "pasilla_differential_expression.csv"
NORMALIZED_PATH = RUNTIME_ROOT / "pasilla_normalized_counts.tsv"
PANEL_PATH = RUNTIME_ROOT / "pasilla_panel_review.tsv"
SUMMARY_PATH = RUNTIME_ROOT / "pasilla_summary.json"

RESULT_COLUMNS = [
    "gene_id",
    "baseMean",
    "log2FoldChange",
    "lfcSE",
    "stat",
    "pvalue",
    "padj",
    "direction",
]

PANEL_COLUMNS = [
    "gene_id",
    "review_bucket",
    "report_priority",
    "note",
    "release_baseMean",
    "release_log2FoldChange",
    "release_padj",
    "reference_log2FoldChange",
    "reference_padj",
    "release_significant",
    "reference_significant",
    "stabilized_abs_log2FoldChange",
    "follow_up_action",
    "manual_review_rank",
    "final_direction",
]


def classify_direction(value: float) -> str:
    if pd.isna(value):
        return "ns"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "ns"


def build_release_design(config: dict) -> str:
    return "~" + " + ".join(config["design_factors"])


def build_reference_design(config: dict) -> str:
    return f"~{config['contrast'][0]}"


def resolve_runtime_path(path_str: str) -> Path:
    path = Path(path_str)
    if RUNTIME_ROOT != Path("/root") and path.is_absolute() and str(path).startswith("/root/"):
        return RUNTIME_ROOT / path.relative_to("/root")
    return path


def load_inputs():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    counts = pd.read_csv(resolve_runtime_path(config["count_matrix"]), sep="\t", index_col=0)
    metadata = pd.read_csv(resolve_runtime_path(config["sample_metadata"]), sep="\t").set_index("sample_id")
    panel = pd.read_csv(resolve_runtime_path(config["panel_file"]), sep="\t")

    counts_t = counts.T.loc[metadata.index]
    genes_to_keep = counts_t.columns[counts_t.sum(axis=0) >= config["min_total_counts"]]
    counts_t = counts_t.loc[:, genes_to_keep]

    for factor in config["design_factors"]:
        metadata[factor] = metadata[factor].astype("category")

    return config, counts_t, metadata, panel


def run_model(counts_t: pd.DataFrame, metadata: pd.DataFrame, design: str, config: dict):
    inference = DefaultInference(n_cpus=1)
    dds = DeseqDataSet(
        counts=counts_t,
        metadata=metadata.copy(),
        design=design,
        refit_cooks=True,
        inference=inference,
    )
    dds.deseq2()

    stats = DeseqStats(
        dds,
        contrast=config["contrast"],
        alpha=config["alpha"],
        inference=inference,
    )
    stats.summary()

    results = (
        stats.results_df.reset_index()
        .rename(columns={"index": "gene_id"})
        .loc[:, ["gene_id", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj"]]
    )
    results["direction"] = results["log2FoldChange"].apply(classify_direction)
    raw_results = results.sort_values(
        by=["padj", "log2FoldChange", "gene_id"],
        ascending=[True, False, True],
        na_position="last",
    ).reset_index(drop=True)

    condition_coeff = next(
        column for column in dds.obsm["design_matrix"].columns if column.startswith(f"{config['contrast'][0]}[")
    )
    stats.lfc_shrink(coeff=condition_coeff)
    shrunk = (
        stats.results_df.reset_index()
        .rename(columns={"index": "gene_id"})
        .loc[:, ["gene_id", "log2FoldChange"]]
        .rename(columns={"log2FoldChange": "stabilized_log2FoldChange"})
    )

    normalized = pd.DataFrame(
        dds.layers["normed_counts"],
        index=dds.obs_names,
        columns=dds.var_names,
    )

    return raw_results, normalized, shrunk


def build_panel_review(
    panel: pd.DataFrame,
    release: pd.DataFrame,
    reference: pd.DataFrame,
    shrunk_release: pd.DataFrame,
    alpha: float,
):
    merged = (
        panel.merge(
            release[
                [
                    "gene_id",
                    "baseMean",
                    "log2FoldChange",
                    "padj",
                    "direction",
                ]
            ].rename(
                columns={
                    "baseMean": "release_baseMean",
                    "log2FoldChange": "release_log2FoldChange",
                    "padj": "release_padj",
                    "direction": "final_direction",
                }
            ),
            on="gene_id",
            how="left",
        )
        .merge(
            reference[
                [
                    "gene_id",
                    "log2FoldChange",
                    "padj",
                ]
            ].rename(
                columns={
                    "log2FoldChange": "reference_log2FoldChange",
                    "padj": "reference_padj",
                }
            ),
            on="gene_id",
            how="left",
        )
        .merge(shrunk_release, on="gene_id", how="left")
    )

    merged["release_significant"] = merged["release_padj"].fillna(1.0) < alpha
    merged["reference_significant"] = merged["reference_padj"].fillna(1.0) < alpha
    merged["stabilized_abs_log2FoldChange"] = merged["stabilized_log2FoldChange"].abs()

    def classify(row: pd.Series) -> str:
        if row["release_significant"] and row["reference_significant"]:
            return "ready_for_release"
        if row["release_significant"] and not row["reference_significant"]:
            return "release_with_caution"
        if row["reference_significant"] and not row["release_significant"]:
            return "needs_manual_review"
        return "no_follow_up"

    merged["follow_up_action"] = merged.apply(classify, axis=1)
    merged["manual_review_rank"] = pd.Series(pd.NA, index=merged.index, dtype="Int64")
    manual_review = merged[merged["follow_up_action"] == "needs_manual_review"].sort_values(
        by=["stabilized_abs_log2FoldChange", "gene_id"],
        ascending=[False, True],
    )
    merged.loc[manual_review.index, "manual_review_rank"] = list(range(1, len(manual_review) + 1))
    merged["final_direction"] = merged["final_direction"].fillna("ns")
    merged["stabilized_abs_log2FoldChange"] = merged["stabilized_abs_log2FoldChange"].fillna(0.0)

    return (
        merged.loc[:, PANEL_COLUMNS]
        .sort_values(by=["report_priority", "review_bucket", "gene_id"])
        .reset_index(drop=True)
    )


def build_summary(config: dict, metadata: pd.DataFrame, release: pd.DataFrame, panel_review: pd.DataFrame):
    significant = release[release["padj"].fillna(1.0) < config["alpha"]].copy()
    up = significant[significant["direction"] == "up"]["gene_id"].tolist()
    down = significant[significant["direction"] == "down"]["gene_id"].tolist()
    release_panel = panel_review.loc[panel_review["release_significant"], "gene_id"].tolist()
    manual_review = (
        panel_review.loc[panel_review["follow_up_action"] == "needs_manual_review"]
        .sort_values(by="manual_review_rank")["gene_id"]
        .tolist()
    )
    action_counts = (
        panel_review.groupby("follow_up_action")
        .size()
        .reindex(
            [
                "ready_for_release",
                "release_with_caution",
                "needs_manual_review",
                "no_follow_up",
            ],
            fill_value=0,
        )
        .to_dict()
    )

    return {
        "comparison": "treated vs untreated",
        "release_design_factors": config["design_factors"],
        "sensitivity_design": build_reference_design(config),
        "sample_count": int(len(metadata)),
        "tested_gene_count": int(len(release)),
        "significant_up_count": int(len(up)),
        "significant_down_count": int(len(down)),
        "release_panel_gene_count": int(len(release_panel)),
        "manual_review_gene_count": int(len(manual_review)),
        "release_panel_genes": release_panel,
        "manual_review_shortlist": manual_review,
        "top_up_genes": up[: config["report_top_n"]],
        "top_down_genes": down[: config["report_top_n"]],
        "follow_up_action_counts": action_counts,
    }


def main():
    config, counts_t, metadata, panel = load_inputs()
    release, normalized, shrunk_release = run_model(counts_t, metadata, build_release_design(config), config)
    reference, _, _ = run_model(counts_t, metadata, build_reference_design(config), config)
    panel_review = build_panel_review(panel, release, reference, shrunk_release, config["alpha"])
    summary = build_summary(config, metadata, release, panel_review)

    release.loc[:, RESULT_COLUMNS].to_csv(RESULT_PATH, index=False)
    normalized.to_csv(NORMALIZED_PATH, sep="\t")
    panel_review.to_csv(PANEL_PATH, sep="\t", index=False)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY
