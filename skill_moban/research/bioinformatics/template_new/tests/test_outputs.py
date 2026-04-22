import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats


OUTPUT_DIR = Path("/root/answer")
BROKEN_DIR = Path("/root/environment/broken_outputs")
PANEL_PATH = Path("/root/environment/data/gene_panel/priority_panel.tsv")
METADATA_PATH = Path("/root/environment/data/metadata/sample_metadata.tsv")
CONFIG_PATH = Path("/root/environment/data/gene_panel/analysis_config.json")
COUNTS_PATH = Path("/root/environment/data/counts/raw_counts.tsv")
ANNOTATION_PATH = Path("/services/panel-annotation/annotations.tsv")

REQUIRED_RESULT_COLUMNS = [
    "gene_id",
    "base_mean",
    "log2_fold_change",
    "lfc_se",
    "stat",
    "pvalue",
    "padj",
    "direction",
]

REQUIRED_DIAGNOSTIC_COLUMNS = [
    "gene_id",
    "review_bucket",
    "report_priority",
    "note",
    "baseline_base_mean",
    "baseline_log2_fold_change",
    "baseline_lfc_se",
    "baseline_stat",
    "baseline_pvalue",
    "baseline_padj",
    "baseline_direction",
    "corrected_log2_fold_change",
    "corrected_base_mean",
    "corrected_lfc_se",
    "corrected_stat",
    "corrected_pvalue",
    "corrected_padj",
    "corrected_direction",
    "baseline_significant",
    "corrected_significant",
    "diagnostic_status",
    "reportable",
    "final_direction",
    "diagnosis_note",
    "display_name",
    "summary_label",
]


def _run_reference_deseq(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    design: str,
    contrast: list[str],
    alpha: float,
) -> pd.DataFrame:
    inference = DefaultInference(n_cpus=1)
    dds = DeseqDataSet(
        counts=counts,
        metadata=metadata,
        design=design,
        refit_cooks=True,
        inference=inference,
    )
    dds.deseq2()
    ds = DeseqStats(
        dds,
        contrast=contrast,
        alpha=alpha,
        inference=inference,
    )
    ds.summary()
    results = ds.results_df.reset_index().rename(
        columns={
            "baseMean": "base_mean",
            "log2FoldChange": "log2_fold_change",
            "lfcSE": "lfc_se",
        }
    )
    results["direction"] = results["log2_fold_change"].apply(lambda value: "up" if value > 0 else "down")
    return results


@lru_cache(maxsize=1)
def reference_bundle() -> dict[str, object]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    counts = pd.read_csv(COUNTS_PATH, sep="\t", index_col=0).T
    metadata = pd.read_csv(METADATA_PATH, sep="\t").set_index("sample_id")
    panel = pd.read_csv(PANEL_PATH, sep="\t")
    annotations = pd.read_csv(ANNOTATION_PATH, sep="\t")
    counts = counts.loc[metadata.index]
    counts = counts.loc[:, counts.sum(axis=0) >= config["min_total_counts"]]

    corrected_results = _run_reference_deseq(
        counts,
        metadata,
        "~" + " + ".join(config["design_factors"]),
        config["contrast"],
        config["alpha"],
    )
    baseline_results = _run_reference_deseq(
        counts,
        metadata,
        f"~{config['contrast'][0]}",
        config["contrast"],
        config["alpha"],
    )

    diagnostics = (
        panel.merge(
            corrected_results.loc[:, ["gene_id", "log2_fold_change", "padj", "direction"]],
            on="gene_id",
            how="left",
        )
        .rename(
            columns={
                "log2_fold_change": "corrected_log2_fold_change",
                "padj": "corrected_padj",
                "direction": "corrected_direction",
            }
        )
        .merge(
            baseline_results.loc[:, ["gene_id", "log2_fold_change", "padj", "direction"]],
            on="gene_id",
            how="left",
        )
        .rename(
            columns={
                "log2_fold_change": "baseline_log2_fold_change",
                "padj": "baseline_padj",
                "direction": "baseline_direction",
            }
        )
        .merge(annotations, on=["gene_id", "review_bucket"], how="left")
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
    diagnostics = diagnostics.sort_values(
        ["report_priority", "corrected_padj", "baseline_padj", "gene_id"],
        na_position="last",
    ).reset_index(drop=True)
    significant = diagnostics[diagnostics["reportable"]].reset_index(drop=True)

    return {
        "config": config,
        "diagnostics": diagnostics,
        "significant": significant,
        "corrected_results": corrected_results,
    }


def test_required_outputs_exist_and_parse() -> None:
    result_path = OUTPUT_DIR / "differential_expression.csv"
    sig_path = OUTPUT_DIR / "significant_genes.tsv"
    norm_path = OUTPUT_DIR / "normalized_counts.tsv"
    diagnostics_path = OUTPUT_DIR / "panel_diagnostics.tsv"
    report_path = OUTPUT_DIR / "report.json"

    assert result_path.exists()
    assert sig_path.exists()
    assert norm_path.exists()
    assert diagnostics_path.exists()
    assert report_path.exists()

    results = pd.read_csv(result_path)
    significant = pd.read_csv(sig_path, sep="\t")
    normalized = pd.read_csv(norm_path, sep="\t", index_col=0)
    diagnostics = pd.read_csv(diagnostics_path, sep="\t")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert list(results.columns) == REQUIRED_RESULT_COLUMNS
    assert len(results) == 9921
    assert results["gene_id"].is_unique
    assert set(significant["gene_id"]).issubset(set(results["gene_id"]))
    assert set(REQUIRED_DIAGNOSTIC_COLUMNS).issubset(set(diagnostics.columns))
    assert set(normalized.columns) == set(pd.read_csv(METADATA_PATH, sep="\t")["sample_id"])
    assert set(report) == {
        "contrast",
        "n_tested_genes",
        "n_significant_genes",
        "upregulated_genes",
        "downregulated_genes",
        "panel_summary",
        "diagnostic_summary",
        "notes",
    }


def test_panel_significant_behavior_matches_corrected_analysis() -> None:
    expected = reference_bundle()
    significant = pd.read_csv(OUTPUT_DIR / "significant_genes.tsv", sep="\t")
    diagnostics = pd.read_csv(OUTPUT_DIR / "panel_diagnostics.tsv", sep="\t")
    panel_significant = significant[significant["is_panel_gene"]].copy()

    assert set(panel_significant["gene_id"]) == set(expected["significant"]["gene_id"])
    assert set(panel_significant["diagnostic_status"]) == {
        "stable_treatment_signal",
        "rescued_after_adjustment",
    }
    assert set(diagnostics["diagnostic_status"]) == {
        "stable_treatment_signal",
        "rescued_after_adjustment",
        "nuisance_sensitive_drop",
    }
    assert set(diagnostics.loc[diagnostics["reportable"], "gene_id"]) == set(panel_significant["gene_id"])


def test_report_is_consistent_with_significant_gene_table() -> None:
    expected = reference_bundle()
    significant = pd.read_csv(OUTPUT_DIR / "significant_genes.tsv", sep="\t")
    diagnostics = pd.read_csv(OUTPUT_DIR / "panel_diagnostics.tsv", sep="\t")
    panel_significant = significant[significant["is_panel_gene"]].copy()
    report = json.loads((OUTPUT_DIR / "report.json").read_text(encoding="utf-8"))

    assert report["n_tested_genes"] == 9921
    assert report["n_significant_genes"] == len(significant)
    assert set(report["upregulated_genes"]) == set(
        significant.loc[significant["direction"] == "up", "gene_id"]
    )
    assert set(report["downregulated_genes"]) == set(
        significant.loc[significant["direction"] == "down", "gene_id"]
    )
    assert report["panel_summary"]["diagnostic_status_counts"] == (
        panel_significant.groupby("diagnostic_status").size().to_dict()
    )
    assert set(report["panel_summary"]["reportable_genes"]) == set(panel_significant["gene_id"])
    assert report["panel_summary"]["n_reportable_panel_genes"] == len(panel_significant)
    assert report["diagnostic_summary"]["panel_gene_count"] == len(diagnostics)
    assert report["diagnostic_summary"]["reportable_gene_count"] == len(expected["significant"])
    assert report["diagnostic_summary"]["status_counts"] == diagnostics.groupby("diagnostic_status").size().to_dict()
    assert report["contrast"]["baseline_design_formula"] == f"~{expected['config']['contrast'][0]}"
    assert report["contrast"]["corrected_design_formula"] == "~" + " + ".join(expected["config"]["design_factors"])


def test_normalized_counts_cover_panel_and_sample_contract() -> None:
    normalized = pd.read_csv(OUTPUT_DIR / "normalized_counts.tsv", sep="\t", index_col=0)
    diagnostics = pd.read_csv(OUTPUT_DIR / "panel_diagnostics.tsv", sep="\t")
    significant = pd.read_csv(OUTPUT_DIR / "significant_genes.tsv", sep="\t")
    panel = pd.read_csv(PANEL_PATH, sep="\t")

    assert normalized.shape[1] == 7
    assert set(significant["gene_id"]).issubset(set(normalized.index))
    assert set(panel["gene_id"]).issubset(set(normalized.index))
    assert set(diagnostics["gene_id"]) == set(panel["gene_id"])
    assert (normalized.loc[list(significant["gene_id"])].sum(axis=1) > 0).all()


def test_guardrail_outputs_do_not_match_broken_behavior() -> None:
    significant = pd.read_csv(OUTPUT_DIR / "significant_genes.tsv", sep="\t")
    broken_significant = pd.read_csv(BROKEN_DIR / "significant_genes.tsv", sep="\t")
    diagnostics = pd.read_csv(OUTPUT_DIR / "panel_diagnostics.tsv", sep="\t")
    panel_significant = significant[significant["is_panel_gene"]].copy()
    report = json.loads((OUTPUT_DIR / "report.json").read_text(encoding="utf-8"))
    broken_report = json.loads((BROKEN_DIR / "report.json").read_text(encoding="utf-8"))

    assert set(panel_significant["gene_id"]) != set(broken_significant["gene_id"])
    assert report["panel_summary"] != broken_report["panel_summary"]
    assert report["contrast"]["corrected_design_formula"] != report["contrast"]["baseline_design_formula"]
    assert "type" in report["contrast"]["corrected_design_formula"]
    assert "condition" in report["contrast"]["corrected_design_formula"]
    assert set(diagnostics.loc[diagnostics["diagnostic_status"] == "nuisance_sensitive_drop", "gene_id"]).isdisjoint(
        set(panel_significant["gene_id"])
    )
