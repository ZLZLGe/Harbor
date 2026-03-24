import os
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
MAPPING_CSV = OUTPUT_DIR / "mro_taxonomy_mapping.csv"
HIERARCHY_CSV = OUTPUT_DIR / "mro_taxonomy_hierarchy.csv"


def load_mapping():
    return pd.read_csv(MAPPING_CSV)


def load_hierarchy():
    return pd.read_csv(HIERARCHY_CSV)


def input_row_count():
    return sum(
        len(pd.read_csv(path))
        for path in [
            DATA_DIR / "grainger_mro_catalog.csv",
            DATA_DIR / "mcmaster_mro_catalog.csv",
            DATA_DIR / "fastenal_mro_catalog.csv",
        ]
    )


def find_unique_row(df, supplier, keywords):
    subset = df[df["supplier"] == supplier]
    mask = subset["supplier_category_path"].str.lower().apply(
        lambda text: all(keyword in text for keyword in keywords)
    )
    matches = subset[mask]
    assert len(matches) == 1, f"{supplier} with keywords {keywords} matched {len(matches)} rows"
    return matches.iloc[0]


def hierarchy_columns():
    return [f"procurement_family_l{i}" for i in range(1, 6)]


def test_output_files_exist():
    assert MAPPING_CSV.exists(), "mro_taxonomy_mapping.csv not found"
    assert HIERARCHY_CSV.exists(), "mro_taxonomy_hierarchy.csv not found"


def test_mapping_schema_and_row_count():
    df = load_mapping()
    required = [
        "supplier",
        "supplier_category_path",
        "source_depth",
        "normalized_leaf",
        "procurement_family_l1",
        "procurement_family_l2",
        "procurement_family_l3",
        "procurement_family_l4",
        "procurement_family_l5",
    ]
    assert list(df.columns) == required, df.columns.tolist()
    assert len(df) == input_row_count(), (len(df), input_row_count())
    assert not df[["supplier", "supplier_category_path", "normalized_leaf", "procurement_family_l1"]].isna().any().any()
    assert df["source_depth"].between(3, 5).all()


def test_hierarchy_schema_and_uniqueness():
    df = load_hierarchy()
    assert list(df.columns) == hierarchy_columns()
    assert not df.duplicated().any()
    assert df["procurement_family_l1"].notna().all()


def test_supplier_coverage():
    df = load_mapping()
    assert set(df["supplier"]) == {"grainger", "mcmaster", "fastenal"}
    for supplier in ["grainger", "mcmaster", "fastenal"]:
        assert (df["supplier"] == supplier).sum() == 30


def test_top_level_family_count():
    df = load_mapping()
    count = df["procurement_family_l1"].nunique()
    assert 8 <= count <= 14, count


def test_hierarchy_consistency():
    df = load_mapping()
    for _, row in df.iterrows():
        for level in range(2, 6):
            if pd.notna(row[f"procurement_family_l{level}"]):
                assert pd.notna(row[f"procurement_family_l{level - 1}"])


def test_category_naming_rules():
    vendor_words = {"grainger", "mcmaster", "fastenal"}
    names = []
    for df in [load_mapping(), load_hierarchy()]:
        for col in hierarchy_columns():
            names.extend(df[col].dropna().astype(str).tolist())

    for name in names:
        clean = name.lower()
        assert not any(vendor in clean for vendor in vendor_words), name
        assert "::" not in name and " / " not in name and " > " not in name, name
        tokens = [part.strip() for part in clean.replace("|", " ").split() if part.strip()]
        assert 1 <= len(tokens) <= 5, (name, len(tokens))


def test_fastener_anchor_alignment():
    df = load_mapping()
    rows = [
        find_unique_row(df, "grainger", ["hex", "bolt"]),
        find_unique_row(df, "mcmaster", ["hex", "cap", "screw"]),
        find_unique_row(df, "fastenal", ["hex", "cap", "screw"]),
    ]
    assert len({row["procurement_family_l1"] for _, row in pd.DataFrame(rows).iterrows()}) == 1


def test_glove_anchor_alignment():
    df = load_mapping()
    rows = [
        find_unique_row(df, "grainger", ["nitrile", "glove"]),
        find_unique_row(df, "mcmaster", ["nitrile", "glove"]),
        find_unique_row(df, "fastenal", ["nitrile", "glove"]),
    ]
    assert len({row["procurement_family_l1"] for _, row in pd.DataFrame(rows).iterrows()}) == 1


def test_hydraulic_anchor_alignment():
    df = load_mapping()
    rows = [
        find_unique_row(df, "grainger", ["two", "wire", "hose"]),
        find_unique_row(df, "mcmaster", ["two", "wire", "hose"]),
        find_unique_row(df, "fastenal", ["two", "wire", "hose"]),
    ]
    assert len({row["procurement_family_l1"] for _, row in pd.DataFrame(rows).iterrows()}) == 1


def test_cross_supplier_mix():
    df = load_mapping()
    family_counts = (
        df.groupby("procurement_family_l1")["supplier"].nunique().sort_values(ascending=False)
    )
    assert (family_counts == 3).sum() >= 7, family_counts.to_dict()


def test_normalized_leaf_quality():
    df = load_mapping()
    for leaf in df["normalized_leaf"].dropna():
        leaf = str(leaf)
        assert leaf == leaf.lower()
        assert "&" not in leaf and "-" not in leaf and "/" not in leaf and "::" not in leaf
        assert 1 <= len(leaf.split()) <= 4


def test_hierarchy_matches_mapping():
    mapping = load_mapping()
    hierarchy = load_hierarchy()
    unique_mapping = mapping[hierarchy_columns()].drop_duplicates().reset_index(drop=True)
    merged = hierarchy.merge(unique_mapping, on=hierarchy_columns(), how="left", indicator=True)
    assert (merged["_merge"] == "both").all()


def test_depth_coverage():
    df = load_mapping()
    l4_rate = df["procurement_family_l4"].notna().mean()
    l5_rate = df["procurement_family_l5"].notna().mean()
    assert l4_rate >= 0.70, l4_rate
    assert l5_rate >= 0.50, l5_rate


def test_delimiters_normalized():
    df = load_mapping()
    assert not df["supplier_category_path"].str.contains(" :: ", regex=False).any()
    assert not df["supplier_category_path"].str.contains(" / ", regex=False).any()
    assert df["supplier_category_path"].str.contains(" > ", regex=False).all()


def test_subfamily_diversity():
    df = load_mapping()
    child_counts = (
        df.groupby("procurement_family_l1")["procurement_family_l2"].nunique().sort_values(ascending=False)
    )
    assert (child_counts >= 2).sum() >= 6, child_counts.to_dict()
