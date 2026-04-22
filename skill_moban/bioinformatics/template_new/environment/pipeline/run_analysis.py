#!/usr/bin/env python3

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats


CONFIG_PATH = Path("/root/environment/data/gene_panel/analysis_config.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_inputs(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    counts = pd.read_csv(config["count_matrix"], sep="\t", index_col=0).T
    metadata = pd.read_csv(config["sample_metadata"], sep="\t").set_index("sample_id")
    panel = pd.read_csv(config["panel_file"], sep="\t")
    counts = counts.loc[metadata.index]
    genes_to_keep = counts.columns[counts.sum(axis=0) >= config["min_total_counts"]]
    counts = counts[genes_to_keep]
    return counts, metadata, panel


def build_design_formula(config: dict) -> str:
    return f"~{config['design_factors'][-1]}"


def run_deseq(counts: pd.DataFrame, metadata: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    inference = DefaultInference(n_cpus=1)
    dds = DeseqDataSet(
        counts=counts,
        metadata=metadata,
        design=build_design_formula(config),
        refit_cooks=True,
        inference=inference,
    )
    dds.deseq2()

    ds = DeseqStats(
        dds,
        contrast=config["contrast"],
        alpha=config["alpha"],
        inference=inference,
    )
    ds.summary()

    results = (
        ds.results_df.reset_index()
        .rename(
            columns={
                "baseMean": "base_mean",
                "log2FoldChange": "log2_fold_change",
                "lfcSE": "lfc_se",
            }
        )
        .loc[:, ["gene_id", "base_mean", "log2_fold_change", "lfc_se", "stat", "pvalue", "padj"]]
    )
    results["direction"] = results["log2_fold_change"].apply(lambda value: "up" if value > 0 else "down")

    normalized = pd.DataFrame(
        dds.layers["normed_counts"],
        index=dds.obs_names,
        columns=dds.var_names,
    ).T

    return results, normalized


def annotate_panel_genes(config: dict, gene_ids: list[str]) -> pd.DataFrame:
    if not gene_ids:
        return pd.DataFrame(columns=["gene_id", "display_name", "review_bucket", "summary_label"])

    params = urllib.parse.urlencode({"genes": ",".join(gene_ids)})
    url = f"{config['annotation_service_url']}?{params}"
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return pd.DataFrame(payload["annotations"])


def build_outputs(
    output_dir: Path,
    config: dict,
    panel: pd.DataFrame,
    results: pd.DataFrame,
    normalized: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    results.to_csv(output_dir / "differential_expression.csv", index=False)
    normalized.to_csv(output_dir / "normalized_counts.tsv", sep="\t")

    panel_results = results.merge(panel, on="gene_id", how="inner")
    significant = panel_results[panel_results["padj"].fillna(1.0) < config["alpha"]].copy()
    significant = significant.sort_values(["report_priority", "padj", "pvalue", "gene_id"])

    annotations = annotate_panel_genes(config, significant["gene_id"].tolist())
    if not annotations.empty:
        significant = significant.merge(annotations, on=["gene_id", "review_bucket"], how="left")

    significant.to_csv(output_dir / "significant_genes.tsv", sep="\t", index=False)

    bucket_counts = significant.groupby("review_bucket").size().to_dict()
    report = {
        "contrast": {
            "design_formula": build_design_formula(config),
            "contrast": config["contrast"],
            "alpha": config["alpha"],
        },
        "n_tested_genes": int(len(results)),
        "n_significant_genes": int(len(significant)),
        "upregulated_genes": significant.loc[significant["direction"] == "up", "gene_id"].tolist(),
        "downregulated_genes": significant.loc[significant["direction"] == "down", "gene_id"].tolist(),
        "panel_summary": {
            "bucket_counts": bucket_counts,
            "top_panel_genes": significant.head(config["report_top_n"])["gene_id"].tolist(),
        },
        "notes": [
            "Outputs were generated from the configured bulk RNA-seq count matrix.",
            "Panel summary is restricted to genes present in the supplied review panel.",
        ],
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output)
    config = load_config()
    counts, metadata, panel = load_inputs(config)
    results, normalized = run_deseq(counts, metadata, config)
    build_outputs(output_dir, config, panel, results, normalized)


if __name__ == "__main__":
    main()
