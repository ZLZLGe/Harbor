import os
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))

MAPPING_CSV = OUTPUT_DIR / "course_transfer_mapping.csv"
HIERARCHY_CSV = OUTPUT_DIR / "subject_taxonomy_hierarchy.csv"
SUMMARY_CSV = OUTPUT_DIR / "transfer_overlap_summary.csv"


def load_mapping():
    return pd.read_csv(MAPPING_CSV)


def load_hierarchy():
    return pd.read_csv(HIERARCHY_CSV)


def load_summary():
    return pd.read_csv(SUMMARY_CSV)


def input_row_count():
    redwood = sum(1 for _ in open(DATA_DIR / "redwood_school_catalog.jsonl", "r", encoding="utf-8"))
    return (
        len(pd.read_csv(DATA_DIR / "northbridge_course_catalog.csv"))
        + redwood
        + len(pd.read_csv(DATA_DIR / "lakeside_program_catalog.tsv", sep="\t"))
    )


def hierarchy_columns():
    return [f"subject_area_l{i}" for i in range(1, 5)]


def find_course(df, university, keyword):
    subset = df[df["university"] == university]
    matches = subset[subset["course_title"].str.lower().str.contains(keyword)]
    assert len(matches) == 1, f"{university} keyword {keyword} matched {len(matches)} rows"
    return matches.iloc[0]


def test_output_files_exist():
    assert MAPPING_CSV.exists(), "course_transfer_mapping.csv not found"
    assert HIERARCHY_CSV.exists(), "subject_taxonomy_hierarchy.csv not found"
    assert SUMMARY_CSV.exists(), "transfer_overlap_summary.csv not found"


def test_mapping_schema_and_row_count():
    df = load_mapping()
    required = [
        "university",
        "course_code",
        "course_title",
        "source_course_path",
        "credit_units",
        "source_depth",
        "normalized_course_title",
        "equivalency_group",
        "subject_area_l1",
        "subject_area_l2",
        "subject_area_l3",
        "subject_area_l4",
    ]
    assert list(df.columns) == required, df.columns.tolist()
    assert len(df) == input_row_count(), (len(df), input_row_count())
    assert df["source_depth"].between(4, 4).all()
    assert not df[["university", "course_code", "course_title", "equivalency_group", "subject_area_l1"]].isna().any().any()


def test_hierarchy_schema_and_uniqueness():
    df = load_hierarchy()
    assert list(df.columns) == hierarchy_columns()
    assert not df.duplicated().any()
    assert df.notna().all().all()


def test_summary_schema_and_consistency():
    summary = load_summary()
    required = [
        "equivalency_group",
        "subject_area_l1",
        "subject_area_l2",
        "subject_area_l3",
        "subject_area_l4",
        "university_count",
        "course_count",
        "min_credit_units",
        "max_credit_units",
    ]
    assert list(summary.columns) == required, summary.columns.tolist()

    mapping = load_mapping()
    regrouped = (
        mapping.groupby(["equivalency_group", *hierarchy_columns()], as_index=False)
        .agg(
            university_count=("university", "nunique"),
            course_count=("course_code", "count"),
            min_credit_units=("credit_units", "min"),
            max_credit_units=("credit_units", "max"),
        )
        .sort_values(["equivalency_group"])
        .reset_index(drop=True)
    )
    merged = summary.sort_values(["equivalency_group"]).reset_index(drop=True).merge(
        regrouped,
        on=["equivalency_group", *hierarchy_columns(), "university_count", "course_count", "min_credit_units", "max_credit_units"],
        how="outer",
        indicator=True,
    )
    assert (merged["_merge"] == "both").all()


def test_university_coverage():
    df = load_mapping()
    assert set(df["university"]) == {"northbridge", "redwood", "lakeside"}
    for university in ["northbridge", "redwood", "lakeside"]:
        assert (df["university"] == university).sum() == 18


def test_source_path_normalization():
    df = load_mapping()
    assert df["source_course_path"].str.contains(" > ", regex=False).all()
    assert not df["source_course_path"].str.contains(" / ", regex=False).any()
    assert not df["source_course_path"].str.contains(" :: ", regex=False).any()


def test_top_level_subject_count():
    df = load_mapping()
    count = df["subject_area_l1"].nunique()
    assert 6 <= count <= 9, count


def test_fixed_four_level_structure():
    df = load_mapping()
    assert df[hierarchy_columns()].notna().all().all()
    for _, row in df.iterrows():
        for level in range(2, 5):
            assert pd.notna(row[f"subject_area_l{level - 1}"])


def test_taxonomy_naming_rules():
    names = []
    blocked = {"northbridge", "redwood", "lakeside"}
    for df in [load_mapping(), load_hierarchy(), load_summary()]:
        for col in hierarchy_columns():
            names.extend(df[col].astype(str).tolist())

    for name in names:
        clean = name.lower()
        assert not any(token in clean for token in blocked), name
        assert " > " not in name and " / " not in name and " :: " not in name, name
        words = [part.strip() for part in clean.replace("|", " ").split() if part.strip()]
        assert 1 <= len(words) <= 5, (name, len(words))


def test_intro_programming_alignment():
    df = load_mapping()
    rows = [
        find_course(df, "northbridge", "introduction to programming"),
        find_course(df, "redwood", "programming fundamentals"),
        find_course(df, "lakeside", "intro to coding"),
    ]
    assert len({row["subject_area_l4"] for row in rows}) == 1
    assert len({row["subject_area_l2"] for row in rows}) == 1


def test_calculus_alignment():
    df = load_mapping()
    rows = [
        find_course(df, "northbridge", "calculus i"),
        find_course(df, "redwood", "calculus 1"),
        find_course(df, "lakeside", "calculus i"),
    ]
    assert len({row["subject_area_l4"] for row in rows}) == 1
    assert len({row["subject_area_l1"] for row in rows}) == 1


def test_general_chemistry_alignment():
    df = load_mapping()
    rows = [
        find_course(df, "northbridge", "general chemistry i"),
        find_course(df, "redwood", "general chemistry 1"),
        find_course(df, "lakeside", "general chemistry i"),
    ]
    assert len({row["subject_area_l3"] for row in rows}) == 1
    assert len({row["subject_area_l2"] for row in rows}) == 1


def test_overlap_summary_strength():
    summary = load_summary()
    assert len(summary) >= 16
    assert (summary["university_count"] == 3).sum() >= 16
    assert (summary["course_count"] >= 3).all()


def test_hierarchy_matches_mapping():
    mapping = load_mapping()
    hierarchy = load_hierarchy()
    unique_mapping = mapping[hierarchy_columns()].drop_duplicates().reset_index(drop=True)
    merged = hierarchy.merge(unique_mapping, on=hierarchy_columns(), how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()


def test_equivalency_group_format():
    df = load_mapping()
    assert df["equivalency_group"].str.match(r"^[a-z0-9_]+$").all()
    per_group = df.groupby("equivalency_group")[hierarchy_columns()].nunique()
    assert (per_group.max(axis=1) == 1).all()


def test_credit_range_reasonable():
    summary = load_summary()
    assert ((summary["max_credit_units"] - summary["min_credit_units"]) <= 1).all()
