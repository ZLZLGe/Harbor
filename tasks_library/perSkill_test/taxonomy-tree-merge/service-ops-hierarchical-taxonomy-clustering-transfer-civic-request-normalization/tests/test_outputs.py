import json
import os
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))

CROSSWALK_CSV = OUTPUT_DIR / "service_request_crosswalk.csv"
HIERARCHY_CSV = OUTPUT_DIR / "service_request_taxonomy_hierarchy.csv"
ROLLUP_CSV = OUTPUT_DIR / "dispatch_sla_rollup.csv"


def hierarchy_columns():
    return [f"unified_issue_l{i}" for i in range(1, 5)]


def read_simple_xlsx(path: Path) -> pd.DataFrame:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as zf:
        worksheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in worksheet.findall(".//a:sheetData/a:row", ns):
        values = []
        for cell in row.findall("a:c", ns):
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                node = cell.find("a:is/a:t", ns)
                values.append(node.text if node is not None else "")
            else:
                node = cell.find("a:v", ns)
                values.append(node.text if node is not None else "")
        rows.append(values)
    return pd.DataFrame(rows[1:], columns=rows[0])


def input_row_count():
    campus_rows = sum(1 for _ in open(DATA_DIR / "campus_maintenance_queue.jsonl", "r", encoding="utf-8"))
    property_rows = len(read_simple_xlsx(DATA_DIR / "residential_portfolio_work_orders.xlsx"))
    return len(pd.read_csv(DATA_DIR / "city311_service_requests.csv")) + campus_rows + property_rows


def load_crosswalk():
    return pd.read_csv(CROSSWALK_CSV)


def load_hierarchy():
    return pd.read_csv(HIERARCHY_CSV)


def load_rollup():
    return pd.read_csv(ROLLUP_CSV)


def find_unique_row(df, source_system, keyword):
    subset = df[df["source_system"] == source_system]
    matches = subset[subset["source_issue_path"].str.lower().str.contains(keyword)]
    assert len(matches) == 1, f"{source_system} keyword {keyword} matched {len(matches)} rows"
    return matches.iloc[0]


def test_output_files_exist():
    assert CROSSWALK_CSV.exists(), "service_request_crosswalk.csv not found"
    assert HIERARCHY_CSV.exists(), "service_request_taxonomy_hierarchy.csv not found"
    assert ROLLUP_CSV.exists(), "dispatch_sla_rollup.csv not found"


def test_crosswalk_schema_and_row_count():
    df = load_crosswalk()
    required = [
        "source_system",
        "request_id",
        "source_issue_path",
        "normalized_issue_path",
        "source_depth",
        "intake_channel",
        "priority_band",
        "sla_target_hours",
        "unified_issue_l1",
        "unified_issue_l2",
        "unified_issue_l3",
        "unified_issue_l4",
    ]
    assert list(df.columns) == required, df.columns.tolist()
    assert len(df) == input_row_count(), (len(df), input_row_count())
    assert df["source_depth"].between(4, 4).all()
    assert not df[["source_system", "request_id", "source_issue_path", "priority_band", "unified_issue_l1"]].isna().any().any()


def test_hierarchy_schema_and_uniqueness():
    df = load_hierarchy()
    assert list(df.columns) == hierarchy_columns()
    assert not df.duplicated().any()
    assert df.notna().all().all()
    assert len(df) == 15


def test_rollup_schema_and_consistency():
    rollup = load_rollup()
    required = [
        "unified_issue_l1",
        "unified_issue_l2",
        "unified_issue_l3",
        "unified_issue_l4",
        "request_count",
        "source_system_count",
        "intake_channel_count",
        "emergency_count",
        "urgent_count",
        "routine_count",
        "median_sla_target_hours",
        "max_sla_target_hours",
    ]
    assert list(rollup.columns) == required, rollup.columns.tolist()

    mapping = load_crosswalk()
    regrouped = (
        mapping.groupby(hierarchy_columns(), as_index=False)
        .agg(
            request_count=("request_id", "count"),
            source_system_count=("source_system", "nunique"),
            intake_channel_count=("intake_channel", "nunique"),
            emergency_count=("priority_band", lambda s: int((s == "emergency").sum())),
            urgent_count=("priority_band", lambda s: int((s == "urgent").sum())),
            routine_count=("priority_band", lambda s: int((s == "routine").sum())),
            median_sla_target_hours=("sla_target_hours", "median"),
            max_sla_target_hours=("sla_target_hours", "max"),
        )
        .sort_values(hierarchy_columns())
        .reset_index(drop=True)
    )
    merged = rollup.sort_values(hierarchy_columns()).reset_index(drop=True).merge(
        regrouped,
        on=[
            *hierarchy_columns(),
            "request_count",
            "source_system_count",
            "intake_channel_count",
            "emergency_count",
            "urgent_count",
            "routine_count",
            "median_sla_target_hours",
            "max_sla_target_hours",
        ],
        how="outer",
        indicator=True,
    )
    assert (merged["_merge"] == "both").all()


def test_source_coverage_and_priority_normalization():
    df = load_crosswalk()
    assert set(df["source_system"]) == {"city311", "campus_facilities", "property_management"}
    for source_system in ["city311", "campus_facilities", "property_management"]:
        assert (df["source_system"] == source_system).sum() == 18
    assert set(df["priority_band"]) == {"emergency", "urgent", "routine"}
    assert set(df["intake_channel"]) == {"phone", "web", "mobile_app", "email", "resident_portal", "front_desk"}


def test_path_normalization_and_fixed_structure():
    df = load_crosswalk()
    assert df["source_issue_path"].str.contains(" > ", regex=False).all()
    assert not df["source_issue_path"].str.contains(" / ", regex=False).any()
    assert not df["source_issue_path"].str.contains(" :: ", regex=False).any()
    assert df["normalized_issue_path"].str.lower().equals(df["normalized_issue_path"])
    assert df[hierarchy_columns()].notna().all().all()


def test_top_level_domain_count_and_mix():
    mapping = load_crosswalk()
    rollup = load_rollup()
    assert 5 <= mapping["unified_issue_l1"].nunique() <= 8
    assert mapping["unified_issue_l1"].nunique() == 6
    assert (rollup["source_system_count"] == 3).all()


def test_taxonomy_naming_rules():
    blocked = {"city", "campus", "property", "tower", "district"}
    names = []
    for df in [load_crosswalk(), load_hierarchy(), load_rollup()]:
        for col in hierarchy_columns():
            names.extend(df[col].astype(str).tolist())

    for name in names:
        clean = name.lower()
        assert " > " not in clean and " / " not in clean and " :: " not in clean, name
        assert not any(token in clean for token in blocked), name
        words = [part.strip() for part in clean.replace("|", " ").split() if part.strip()]
        assert 1 <= len(words) <= 5, (name, len(words))


def test_graffiti_alignment():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "city311", "graffiti"),
        find_unique_row(df, "campus_facilities", "graffiti"),
        find_unique_row(df, "property_management", "graffiti"),
    ]
    assert len({row["unified_issue_l3"] for row in rows}) == 1
    assert len({row["unified_issue_l1"] for row in rows}) == 1


def test_elevator_alignment_and_hotspot_rollup():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "city311", "car stalled"),
        find_unique_row(df, "campus_facilities", "stalled car"),
        find_unique_row(df, "property_management", "car stalled"),
    ]
    assert len({row["unified_issue_l4"] for row in rows}) == 1

    rollup = load_rollup()
    target = rollup[
        (rollup["unified_issue_l3"] == "elevator | outage")
        & (rollup["unified_issue_l4"] == "car | stalled")
    ]
    assert len(target) == 1
    row = target.iloc[0]
    assert row["request_count"] == 6
    assert row["emergency_count"] == 6
    assert row["median_sla_target_hours"] == 2.0
    assert row["max_sla_target_hours"] == 4


def test_water_leak_alignment_and_rollup():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "city311", "ceiling drip"),
        find_unique_row(df, "campus_facilities", "ceiling drip"),
        find_unique_row(df, "property_management", "ceiling drip"),
    ]
    assert len({row["unified_issue_l2"] for row in rows}) == 1
    assert len({row["unified_issue_l4"] for row in rows}) == 1

    rollup = load_rollup()
    target = rollup[
        (rollup["unified_issue_l2"] == "pipe | leak")
        & (rollup["unified_issue_l4"] == "ceiling | drip")
    ]
    assert len(target) == 1
    row = target.iloc[0]
    assert row["request_count"] == 6
    assert row["source_system_count"] == 3
    assert row["emergency_count"] == 6
    assert row["median_sla_target_hours"] == 3.0
    assert row["max_sla_target_hours"] == 6


def test_no_cooling_alignment_and_channel_diversity():
    df = load_crosswalk()
    rows = [
        find_unique_row(df, "city311", "warm apartment"),
        find_unique_row(df, "campus_facilities", "warm room"),
        find_unique_row(df, "property_management", "warm unit"),
    ]
    assert len({row["unified_issue_l3"] for row in rows}) == 1
    assert len({row["unified_issue_l1"] for row in rows}) == 1

    rollup = load_rollup()
    target = rollup[
        (rollup["unified_issue_l3"] == "cooling | outage")
        & (rollup["unified_issue_l4"] == "warm | space")
    ]
    assert len(target) == 1
    row = target.iloc[0]
    assert row["request_count"] == 6
    assert row["urgent_count"] == 6
    assert row["intake_channel_count"] == 4
    assert row["median_sla_target_hours"] == 24.0
    assert row["max_sla_target_hours"] == 48


def test_hierarchy_matches_crosswalk():
    mapping = load_crosswalk()
    hierarchy = load_hierarchy()
    unique_mapping = mapping[hierarchy_columns()].drop_duplicates().reset_index(drop=True)
    merged = hierarchy.merge(unique_mapping, on=hierarchy_columns(), how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()
