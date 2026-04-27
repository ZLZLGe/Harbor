#!/usr/bin/env python3

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats


ANNOTATION_SERVER_PATH = Path("/services/panel-annotation/server.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def build_design_formula(config: dict) -> str:
    return "~" + " + ".join(config["design_factors"])


def build_baseline_formula(config: dict) -> str:
    return f"~{config['contrast'][0]}"


def run_deseq(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    design_formula: str,
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    inference = DefaultInference(n_cpus=1)
    dds = DeseqDataSet(
        counts=counts,
        metadata=metadata,
        design=design_formula,
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


def load_inputs(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    counts = pd.read_csv(config["count_matrix"], sep="\t", index_col=0).T
    metadata = pd.read_csv(config["sample_metadata"], sep="\t").set_index("sample_id")
    panel = pd.read_csv(config["panel_file"], sep="\t")
    counts = counts.loc[metadata.index]
    counts = counts.loc[:, counts.sum(axis=0) >= config.get("min_total_counts", 10)]
    return counts, metadata, panel


def wait_for_annotation_service(url: str, attempts: int = 5) -> None:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"annotation service did not start: {url}")


def ensure_annotation_service(config: dict) -> None:
    probe_url = f"{config['annotation_service_url']}?genes="
    try:
        wait_for_annotation_service(probe_url, attempts=1)
        return
    except Exception:
        pass

    if ANNOTATION_SERVER_PATH.exists():
        subprocess.Popen(
            ["python", str(ANNOTATION_SERVER_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_for_annotation_service(probe_url)


def annotate_panel_genes(config: dict, gene_ids: list[str]) -> pd.DataFrame:
    if not gene_ids:
        return pd.DataFrame(columns=["gene_id", "display_name", "review_bucket", "summary_label"])

    ensure_annotation_service(config)
    params = urllib.parse.urlencode({"genes": ",".join(gene_ids)})
    url = f"{config['annotation_service_url']}?{params}"
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return pd.DataFrame(payload["annotations"])


def build_panel_diagnostics(
    config: dict,
    panel: pd.DataFrame,
    corrected_results: pd.DataFrame,
    baseline_results: pd.DataFrame,
) -> pd.DataFrame:
    diagnostics = (
        panel.merge(
            corrected_results.loc[
                :,
                [
                    "gene_id",
                    "base_mean",
                    "log2_fold_change",
                    "lfc_se",
                    "stat",
                    "pvalue",
                    "padj",
                    "direction",
                ],
            ],
            on="gene_id",
            how="left",
        )
        .rename(
            columns={
                "base_mean": "corrected_base_mean",
                "log2_fold_change": "corrected_log2_fold_change",
                "lfc_se": "corrected_lfc_se",
                "stat": "corrected_stat",
                "pvalue": "corrected_pvalue",
                "padj": "corrected_padj",
                "direction": "corrected_direction",
            }
        )
        .merge(
            baseline_results.loc[
                :,
                [
                    "gene_id",
                    "base_mean",
                    "log2_fold_change",
                    "lfc_se",
                    "stat",
                    "pvalue",
                    "padj",
                    "direction",
                ],
            ],
            on="gene_id",
            how="left",
        )
        .rename(
            columns={
                "base_mean": "baseline_base_mean",
                "log2_fold_change": "baseline_log2_fold_change",
                "lfc_se": "baseline_lfc_se",
                "stat": "baseline_stat",
                "pvalue": "baseline_pvalue",
                "padj": "baseline_padj",
                "direction": "baseline_direction",
            }
        )
    )
    diagnostics["baseline_significant"] = diagnostics["baseline_padj"].fillna(1.0) < config["alpha"]
    diagnostics["corrected_significant"] = diagnostics["corrected_padj"].fillna(1.0) < config["alpha"]

    def classify(row: pd.Series) -> str:
        if row["baseline_significant"] and row["corrected_significant"]:
            return "stable_treatment_signal"
        if row["corrected_significant"] and not row["baseline_significant"]:
            return "rescued_after_adjustment"
        if row["baseline_significant"] and not row["corrected_significant"]:
            return "nuisance_sensitive_drop"
        return "nonreportable_background"

    diagnostics["diagnostic_status"] = diagnostics.apply(classify, axis=1)
    diagnostics["reportable"] = diagnostics["corrected_significant"]
    diagnostics["final_direction"] = diagnostics["corrected_direction"]
    diagnostics["diagnosis_note"] = diagnostics["diagnostic_status"].map(
        {
            "stable_treatment_signal": "Stable treatment-associated hit in both baseline and corrected models.",
            "rescued_after_adjustment": "Recovered only after adding the nuisance-adjustment factor.",
            "nuisance_sensitive_drop": "Baseline-only hit consistent with technical-factor confounding.",
            "nonreportable_background": "Tracked on the review panel but not reportable in the corrected release.",
        }
    )

    annotations = annotate_panel_genes(config, diagnostics["gene_id"].tolist())
    if not annotations.empty:
        diagnostics = diagnostics.merge(annotations, on=["gene_id", "review_bucket"], how="left")

    return diagnostics.sort_values(
        ["report_priority", "corrected_padj", "baseline_padj", "gene_id"],
        na_position="last",
    )


def build_outputs(
    output_dir: Path,
    config: dict,
    panel: pd.DataFrame,
    corrected_results: pd.DataFrame,
    baseline_results: pd.DataFrame,
    normalized: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    corrected_results.to_csv(output_dir / "differential_expression.csv", index=False)
    normalized.to_csv(output_dir / "normalized_counts.tsv", sep="\t")

    diagnostics = build_panel_diagnostics(config, panel, corrected_results, baseline_results)
    diagnostics.to_csv(output_dir / "panel_diagnostics.tsv", sep="\t", index=False)

    significant = corrected_results[corrected_results["padj"].fillna(1.0) < config["alpha"]].copy()
    significant["reportable"] = True
    significant["is_panel_gene"] = significant["gene_id"].isin(set(panel["gene_id"]))

    panel_annotations = diagnostics.loc[
        :,
        ["gene_id", "review_bucket", "display_name", "summary_label", "diagnostic_status", "reportable"],
    ].rename(columns={"reportable": "panel_reportable"})
    significant = significant.merge(panel_annotations, on="gene_id", how="left")
    significant["reportable"] = significant.pop("panel_reportable").fillna(True)
    significant.to_csv(output_dir / "significant_genes.tsv", sep="\t", index=False)

    panel_reportable = diagnostics[diagnostics["reportable"]].copy()
    report = {
        "contrast": {
            "corrected_design_formula": build_design_formula(config),
            "baseline_design_formula": build_baseline_formula(config),
            "contrast": config["contrast"],
            "alpha": config["alpha"],
        },
        "n_tested_genes": int(len(corrected_results)),
        "n_significant_genes": int(len(significant)),
        "upregulated_genes": significant.loc[significant["direction"] == "up", "gene_id"].tolist(),
        "downregulated_genes": significant.loc[significant["direction"] == "down", "gene_id"].tolist(),
        "panel_summary": {
            "diagnostic_status_counts": panel_reportable.groupby("diagnostic_status").size().to_dict(),
            "n_reportable_panel_genes": int(panel_reportable["gene_id"].nunique()),
            "top_panel_genes": panel_reportable.head(config["report_top_n"])["gene_id"].tolist(),
            "reportable_genes": panel_reportable["gene_id"].tolist(),
        },
        "diagnostic_summary": {
            "panel_gene_count": int(len(diagnostics)),
            "reportable_gene_count": int(diagnostics["reportable"].sum()),
            "status_counts": diagnostics.groupby("diagnostic_status").size().to_dict(),
        },
        "notes": [
            "Outputs were generated from the configured bulk RNA-seq count matrix.",
            "Configured technical factors were included in the fitted design.",
            "Panel diagnostics compare the baseline and corrected models on the supplied review panel.",
        ],
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output)
    counts, metadata, panel = load_inputs(config)
    corrected_results, normalized = run_deseq(counts, metadata, build_design_formula(config), config)
    baseline_results, _ = run_deseq(counts, metadata, build_baseline_formula(config), config)
    build_outputs(output_dir, config, panel, corrected_results, baseline_results, normalized)


if __name__ == "__main__":
    main()
