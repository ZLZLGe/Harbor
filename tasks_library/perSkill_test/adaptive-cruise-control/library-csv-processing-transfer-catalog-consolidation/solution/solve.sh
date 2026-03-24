#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

def has_inputs(path: Path) -> bool:
    try:
        return (path / "catalog_export.csv").exists() and (path / "circulation_history.csv").exists()
    except PermissionError:
        return False


base_dir = Path("/root")
if not has_inputs(base_dir):
    base_dir = Path.cwd()

script_path = base_dir / "build_merge_candidates.py"
script_path.write_text(
    """import json
import re
from pathlib import Path

import pandas as pd


def normalize_text(value: str) -> str:
    text = (value or "").lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\\s+", " ", text).strip()
    return text


def normalize_isbn(value: str) -> str:
    text = re.sub(r"[^0-9xX]+", "", value or "")
    return text.upper()


def build_candidate(group: pd.DataFrame, match_basis: str, reason: str) -> dict:
    ordered = group.sort_values("record_id").copy()
    preferred = group.sort_values(
        ["loan_count_2025", "copy_count", "record_id"],
        ascending=[False, False, True],
    ).iloc[0]
    record_ids = ordered["record_id"].tolist()
    merge_ids = [record_id for record_id in record_ids if record_id != preferred["record_id"]]

    return {
        "match_basis": match_basis,
        "normalized_isbn": ordered["normalized_isbn"].iloc[0] if match_basis == "isbn" else "",
        "normalized_title": ordered["normalized_title"].iloc[0],
        "normalized_author": ordered["normalized_author"].iloc[0],
        "format": ordered["format"].iloc[0],
        "preferred_record_id": preferred["record_id"],
        "preferred_loan_count_2025": int(preferred["loan_count_2025"]),
        "merge_record_ids": ";".join(merge_ids),
        "all_record_ids": ";".join(record_ids),
        "member_count": int(len(ordered)),
        "branches_covered": int(ordered["owning_branch"].nunique()),
        "total_copy_count": int(ordered["copy_count"].sum()),
        "recent_loan_count": int(ordered["loan_count_2025"].sum()),
        "title_variant_count": int(ordered["title"].str.strip().nunique()),
        "confidence_reason": reason,
    }


def main() -> None:
    root = Path("/root")
    try:
        has_root_inputs = (root / "catalog_export.csv").exists() and (root / "circulation_history.csv").exists()
    except PermissionError:
        has_root_inputs = False
    if not has_root_inputs:
        root = Path.cwd()

    catalog = pd.read_csv(root / "catalog_export.csv", keep_default_na=False)
    circulation = pd.read_csv(root / "circulation_history.csv", keep_default_na=False)

    catalog = catalog.sort_values("record_id").copy()
    catalog["normalized_isbn"] = catalog["isbn"].map(normalize_isbn)
    catalog["normalized_title"] = catalog["title"].map(normalize_text)
    catalog["normalized_author"] = catalog["author"].map(normalize_text)

    loan_counts = (
        circulation[circulation["checkout_date"].str.startswith("2025-")]
        .groupby("record_id")
        .size()
        .to_dict()
    )
    catalog["loan_count_2025"] = catalog["record_id"].map(lambda value: int(loan_counts.get(value, 0)))

    candidates = []

    isbn_rows = catalog[catalog["normalized_isbn"] != ""].copy()
    for _, group in isbn_rows.groupby(["normalized_isbn", "format"], sort=False):
        if len(group) >= 2:
            candidates.append(
                build_candidate(group, "isbn", "same_normalized_isbn_and_format")
            )

    title_rows = catalog[catalog["normalized_isbn"] == ""].copy()
    for _, group in title_rows.groupby(
        ["normalized_title", "normalized_author", "format", "publication_year", "audience"],
        sort=False,
    ):
        if len(group) >= 2:
            candidates.append(
                build_candidate(
                    group,
                    "title_author",
                    "same_normalized_title_author_year_audience_format",
                )
            )

    output = pd.DataFrame(
        candidates,
        columns=[
            "match_basis",
            "normalized_isbn",
            "normalized_title",
            "normalized_author",
            "format",
            "preferred_record_id",
            "preferred_loan_count_2025",
            "merge_record_ids",
            "all_record_ids",
            "member_count",
            "branches_covered",
            "total_copy_count",
            "recent_loan_count",
            "title_variant_count",
            "confidence_reason",
        ],
    )

    if not output.empty:
        output["basis_rank"] = output["match_basis"].map({"isbn": 0, "title_author": 1})
        output = output.sort_values(
            ["basis_rank", "normalized_title", "preferred_record_id"],
            ascending=[True, True, True],
        ).reset_index(drop=True)
        output.insert(
            0,
            "candidate_id",
            [f"MERGE-{index:03d}" for index in range(1, len(output) + 1)],
        )
        output = output.drop(columns=["basis_rank", "preferred_loan_count_2025"])
    else:
        output.insert(0, "candidate_id", [])

    output.to_csv(root / "catalog_merge_candidates.csv", index=False)

    summary = {
        "candidate_count": int(len(output)),
        "isbn_based_candidates": int((output["match_basis"] == "isbn").sum()) if not output.empty else 0,
        "title_based_candidates": int((output["match_basis"] == "title_author").sum()) if not output.empty else 0,
        "records_flagged_for_merge": int((output["member_count"] - 1).sum()) if not output.empty else 0,
        "preferred_records_with_zero_2025_loans": sorted(
            pd.DataFrame(candidates).loc[
                pd.DataFrame(candidates)["preferred_loan_count_2025"] == 0,
                "preferred_record_id",
            ].tolist()
        )
        if candidates
        else [],
        "max_candidate_size": int(output["member_count"].max()) if not output.empty else 0,
        "total_recent_loan_count": int(output["recent_loan_count"].sum()) if not output.empty else 0,
    }

    with (root / "catalog_merge_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


if __name__ == "__main__":
    main()
""",
    encoding="utf-8",
)
PY

python3 "$( [ -f /root/build_merge_candidates.py ] && echo /root/build_merge_candidates.py || echo ./build_merge_candidates.py )"
