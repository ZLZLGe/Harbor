import os
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))

CROSSWALK_CSV = OUTPUT_DIR / "clinical_service_crosswalk.csv"
HIERARCHY_CSV = OUTPUT_DIR / "clinical_taxonomy_hierarchy.csv"
SUMMARY_CSV = OUTPUT_DIR / "care_navigation_summary.csv"


def load_crosswalk():
    return pd.read_csv(CROSSWALK_CSV)


def load_hierarchy():
    return pd.read_csv(HIERARCHY_CSV)


def load_summary():
    return pd.read_csv(SUMMARY_CSV)


def hierarchy_columns():
    return [f"unified_service_l{i}" for i in range(1, 5 + 1)]


def input_row_count():
    payer_rows = sum(1 for _ in open(DATA_DIR / "payer_benefit_catalog.jsonl", "r", encoding="utf-8"))
    return (
        len(pd.read_csv(DATA_DIR / "hospital_group_services.csv"))
        + payer_rows
        + len(pd.read_csv(DATA_DIR / "telehealth_visit_directory.tsv", sep="\t"))
    )


def find_unique_row(df, source_system, keyword):
    subset = df[df["source_system"] == source_system]
    matches = subset[subset["source_service_path"].str.lower().str.contains(keyword)]
    assert len(matches) == 1, f"{source_system} keyword {keyword} matched {len(matches)} rows"
    return matches.iloc[0]


def test_output_files_exist():
    assert CROSSWALK_CSV.exists(), "clinical_service_crosswalk.csv not found"
    assert HIERARCHY_CSV.exists(), "clinical_taxonomy_hierarchy.csv not found"
    assert SUMMARY_CSV.exists(), "care_navigation_summary.csv not found"


def test_crosswalk_schema_and_row_count():
    df = load_crosswalk()
    required = [
        "source_system",
        "source_service_id",
        "source_service_path",
        "normalized_service_path",
        "source_depth",
        "booking_surface",
        "care_mode",
        "unified_service_l1",
        "unified_service_l2",
        "unified_service_l3",
        "unified_service_l4",
        "unified_service_l5",
    ]
    assert list(df.columns) == required, df.columns.tolist()
    assert len(df) == input_row_count(), (len(df), input_row_count())
    assert df["source_depth"].between(5, 5).all()
    assert not df[["source_system", "source_service_id", "source_service_path", "care_mode", "unified_service_l1"]].isna().any().any()


def test_hierarchy_schema_and_uniqueness():
    df = load_hierarchy()
    assert list(df.columns) == hierarchy_columns()
    assert not df.duplicated().any()
    assert df.notna().all().all()


def test_summary_schema_and_consistency():
    summary = load_summary()
    required = [
        "unified_service_l1",
        "unified_service_l2",
        "unified_service_l3",
        "unified_service_l4",
        "unified_service_l5",
        "source_system_count",
        "booking_surface_count",
        "in_person_count",
        "virtual_count",
        "hybrid_count",
        "ancillary_count",
    ]
    assert list(summary.columns) == required, summary.columns.tolist()

    mapping = load_crosswalk()
    regrouped = (
        mapping.groupby(hierarchy_columns(), as_index=False)
        .agg(
            source_system_count=("source_system", "nunique"),
            booking_surface_count=("booking_surface", "nunique"),
            in_person_count=("care_mode", lambda s: int((s == "in_person").sum())),
            virtual_count=("care_mode", lambda s: int((s == "virtual").sum())),
            hybrid_count=("care_mode", lambda s: int((s == "hybrid").sum())),
            ancillary_count=("care_mode", lambda s: int((s == "ancillary").sum())),
        )
        .sort_values(hierarchy_columns())
        .reset_index(drop=True)
    )

    merged = summary.sort_values(hierarchy_columns()).reset_index(drop=True).merge(
        regrouped,
        on=[
            *hierarchy_columns(),
            "source_system_count",
            "booking_surface_count",
            "in_person_count",
            "virtual_count",
            "hybrid_count",
            "ancillary_count",
        ],
        how="outer",
        indicator=True,
    )
    assert (merged["_merge"] == "both").all()


def test_source_system_coverage():
    df = load_crosswalk()
    assert set(df["source_system"]) == {"hospital_group", "payer_catalog", "telehealth_platform"}
    for source_system in ["hospital_group", "payer_catalog", "telehealth_platform"]:
        assert (df["source_system"] == source_system).sum() == 18
    assert set(df["care_mode"]) == {"in_person", "virtual", "hybrid", "ancillary"}


def test_path_normalization():
    df = load_crosswalk()
    assert df["source_service_path"].str.contains(" > ", regex=False).all()
    assert not df["source_service_path"].str.contains(" / ", regex=False).any()
    assert not df["source_service_path"].str.contains(" :: ", regex=False).any()
    assert df["normalized_service_path"].str.lower().equals(df["normalized_service_path"])


def test_top_level_service_count():
    df = load_crosswalk()
    count = df["unified_service_l1"].nunique()
    assert 7 <= count <= 10, count


def test_fixed_five_level_structure():
    df = load_crosswalk()
    assert df[hierarchy_columns()].notna().all().all()
    for _, row in df.iterrows():
        for level in range(2, 6):
            assert pd.notna(row[f"unified_service_l{level - 1}"])


def test_taxonomy_naming_rules():
    blocked = {"hospital", "payer", "telehealth", "network", "clinic setting", "virtual setting"}
    names = []
    for df in [load_crosswalk(), load_hierarchy(), load_summary()]:
        for col in hierarchy_columns():
            names.extend(df[col].astype(str).tolist())

    for name in names:
        clean = name.lower()
        assert " > " not in clean and " / " not in clean and " :: " not in clean, name
        assert not any(token in clean for token in blocked), name
        tokens = [part.strip() for part in clean.replace("|", " ").split() if part.strip()]
        assert 1 <= len(tokens) <= 5, (name, len(tokens))


def test_summary_totals():
    summary = load_summary()
    assert len(summary) == 18
    total_counts = summary[["in_person_count", "virtual_count", "hybrid_count", "ancillary_count"]].sum(axis=1)
    assert (total_counts == 3).all()


def test_same_day_alignment():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "hospital_group", "video triage"),
        find_unique_row(df, "payer_catalog", "same-day video"),
        find_unique_row(df, "telehealth_platform", "same-day video"),
    ]
    assert len({row["unified_service_l4"] for row in rows}) == 1
    assert len({row["unified_service_l1"] for row in rows}) == 1


def test_prenatal_alignment():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "hospital_group", "routine obstetrics"),
        find_unique_row(df, "payer_catalog", "routine ob"),
        find_unique_row(df, "telehealth_platform", "prenatal routine"),
    ]
    assert len({row["unified_service_l5"] for row in rows}) == 1
    assert len({row["unified_service_l2"] for row in rows}) == 1


def test_knee_replacement_alignment():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "hospital_group", "arthroplasty"),
        find_unique_row(df, "payer_catalog", "knee replacement"),
        find_unique_row(df, "telehealth_platform", "surgical pathways"),
    ]
    assert len({row["unified_service_l3"] for row in rows}) == 1
    assert len({row["unified_service_l1"] for row in rows}) == 1


def test_behavioral_medication_alignment():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "hospital_group", "medication follow-up"),
        find_unique_row(df, "payer_catalog", "medication management"),
        find_unique_row(df, "telehealth_platform", "medication review"),
    ]
    assert len({row["unified_service_l4"] for row in rows}) == 1
    assert len({row["unified_service_l2"] for row in rows}) == 1


def test_cross_source_mix():
    df = load_crosswalk()
    source_counts = df.groupby("unified_service_l1")["source_system"].nunique()
    assert (source_counts == 3).sum() >= 6, source_counts.to_dict()


def test_hierarchy_matches_crosswalk():
    mapping = load_crosswalk()
    hierarchy = load_hierarchy()
    unique_mapping = mapping[hierarchy_columns()].drop_duplicates().reset_index(drop=True)
    merged = hierarchy.merge(unique_mapping, on=hierarchy_columns(), how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()
