#!/usr/bin/env python3
import csv
import os
import subprocess
import sys
from pathlib import Path

from _catalog import load_records
from _record_logic import canonical_comparator_type, canonical_primary_outcome_direction, canonical_row, is_eligible


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
CANDIDATES_PATH = WORKSPACE_ROOT / "data" / "candidate_records.csv"
CSV_PATH = WORKSPACE_ROOT / "included_studies.csv"
BIB_PATH = WORKSPACE_ROOT / "references.bib"
SUMMARY_PATH = WORKSPACE_ROOT / "summary.md"
BUILD_SCRIPT = WORKSPACE_ROOT / "build_submission.py"

AUTHOR_LOOKUP = {
    "study_001": "Che, T. and Yan, C. and Tian, D. and Zhang, X. and Liu, X. and Wu, Z.",
    "study_002": "Pavlou, V. and Cienfuegos, S. and Lin, S. and Ezpeleta, M. and Ready, K. and Varady, K. A.",
    "study_003": "Parr, E. B. and Radford, B. E. and Hall, R. C. and Steventon-Lorenzen, N. and Flint, S. A. and Siviour, Z. and Plessas, C. and Halson, S. L. and Brennan, L. and Kouw, I. W. K. and Johnston, R. D. and Devlin, B. L. and Hawley, J. A.",
    "study_004": "Trico, D. and Masoni, M. C. and Baldi, S. and Cimbalo, N. and Sacchetta, L. and Scozzaro, M. T. and Nesti, G. and Mengozzi, A. and Nesti, L. and Chiriaco, M. and Natali, A.",
}


def load_candidate_ids() -> list[str]:
    with CANDIDATES_PATH.open("r", encoding="utf-8", newline="") as handle:
        return [row["study_id"] for row in csv.DictReader(handle)]


def load_target_records() -> list[dict]:
    candidate_ids = load_candidate_ids()
    records = load_records(candidate_ids)
    return [record for study_id, record in records.items() if is_eligible(record)]


def write_included_studies(target_records: list[dict]) -> None:
    rows = [canonical_row(record) for record in target_records]
    if not rows:
        raise RuntimeError("No eligible studies were derived from the bundled review catalog.")
    fieldnames = list(rows[0].keys())
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def bib_entry(record: dict) -> str:
    authors = AUTHOR_LOOKUP.get(record["study_id"], record["first_author_last_name"])
    title = record["title"].replace("&", "\\&")
    journal = record["journal"].replace("&", "\\&")
    return "\n".join(
        [
            f"@article{{{record['study_id']},",
            f"  author = {{{authors}}},",
            f"  title = {{{title}}},",
            f"  journal = {{{journal}}},",
            f"  year = {{{record['year']}}},",
            f"  doi = {{{record['doi']}}}",
            "}",
        ]
    )


def write_references(target_records: list[dict]) -> None:
    entries = [bib_entry(record) for record in target_records]
    BIB_PATH.write_text("\n\n".join(entries) + "\n", encoding="utf-8")


def render_summary(target_records: list[dict]) -> str:
    benefit_records = []
    active_records = []
    for record in target_records:
        outcome_direction = canonical_primary_outcome_direction(record)
        comparator_type = canonical_comparator_type(record)
        if outcome_direction == "benefit_vs_control":
            benefit_records.append(record)
        if outcome_direction == "similar_to_active_diet":
            active_records.append((record, comparator_type))

    n_trials = len(target_records)
    scope_line = f"This repaired evidence package is limited to {n_trials} randomized studies in adults with type 2 diabetes."

    main_takeaways = (
        "Across the adult T2D trials, time-restricted eating improved glycaemic outcomes relative to passive control conditions in some settings."
    )
    if active_records:
        main_takeaways += (
            " The same evidence base does not show consistent superiority over active dietary comparators, because the trials that compared TRE with structured diet counselling or conventional dieting reported similar or non-inferior glycaemic results rather than clear superiority."
        )

    limitations = (
        "The evidence base remains modest, so the conclusion should stay bounded to the current adult type 2 diabetes trial set and should avoid broader generalization beyond that scope."
    )

    return "\n".join(
        [
            "## Review Scope",
            "",
            scope_line,
            "",
            "## Main Takeaways",
            "",
            main_takeaways,
            "",
            "## Limitations",
            "",
            limitations,
            "",
        ]
    )


def write_summary(target_records: list[dict]) -> None:
    SUMMARY_PATH.write_text(render_summary(target_records), encoding="utf-8")


def run_build() -> None:
    completed = subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    target_records = load_target_records()
    write_included_studies(target_records)
    write_references(target_records)
    write_summary(target_records)
    run_build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
