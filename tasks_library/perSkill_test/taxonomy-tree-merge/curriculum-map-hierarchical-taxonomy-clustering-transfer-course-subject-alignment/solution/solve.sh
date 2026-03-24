#!/bin/bash
set -euo pipefail

cat > /tmp/curriculum_transfer_solver.py <<'PY'
#!/usr/bin/env python3

import json
import os
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))


RULES = [
    {
        "match_any": [["intro", "programming"], ["beginner", "programming"]],
        "equivalency_group": "intro_programming",
        "levels": ("computing | data", "programming | foundation", "coding | basics", "intro | programming"),
    },
    {
        "match_all": ["data", "structure"],
        "equivalency_group": "data_structures",
        "levels": ("computing | data", "programming | foundation", "algorithm | structure", "data | structures"),
    },
    {
        "match_all": ["database"],
        "equivalency_group": "database_systems",
        "levels": ("computing | data", "information | systems", "data | management", "database | design"),
    },
    {
        "match_all": ["operating", "system"],
        "equivalency_group": "operating_systems",
        "levels": ("computing | data", "systems | infrastructure", "platform | runtime", "operating | systems"),
    },
    {
        "match_all": ["statistic"],
        "equivalency_group": "intro_statistics",
        "levels": ("math | analytics", "probability | statistics", "intro | inference", "applied | statistics"),
    },
    {
        "match_all": ["calculus"],
        "equivalency_group": "calculus_i",
        "levels": ("math | analytics", "calculus | modeling", "differential | change", "calculus | one"),
    },
    {
        "match_all": ["linear", "algebra"],
        "equivalency_group": "linear_algebra",
        "levels": ("math | analytics", "algebra | matrix", "vector | systems", "linear | algebra"),
    },
    {
        "match_all": ["discrete"],
        "equivalency_group": "discrete_mathematics",
        "levels": ("math | analytics", "logic | combinatorics", "proof | structures", "discrete | mathematics"),
    },
    {
        "match_all": ["general", "chemistry"],
        "match_none": ["organic"],
        "equivalency_group": "general_chemistry_i",
        "levels": ("chemistry | molecular", "general | chemistry", "atomic | matter", "chemistry | one"),
    },
    {
        "match_all": ["organic", "chemistry"],
        "equivalency_group": "organic_chemistry_i",
        "levels": ("chemistry | molecular", "organic | chemistry", "carbon | reaction", "organic | one"),
    },
    {
        "match_all": ["cell"],
        "equivalency_group": "cell_biology",
        "levels": ("biology | life", "cell | molecular", "structure | function", "cell | biology"),
    },
    {
        "match_all": ["genetic"],
        "equivalency_group": "genetics",
        "levels": ("biology | life", "genetics | heredity", "gene | inheritance", "principles | genetics"),
    },
    {
        "match_all": ["microeconomics"],
        "equivalency_group": "microeconomics",
        "levels": ("economics | policy", "market | behavior", "consumer | firm", "micro | economics"),
    },
    {
        "match_all": ["macroeconomics"],
        "equivalency_group": "macroeconomics",
        "levels": ("economics | policy", "aggregate | systems", "output | policy", "macro | economics"),
    },
    {
        "match_any": [["composition"], ["writing"]],
        "equivalency_group": "college_writing",
        "levels": ("writing | humanities", "academic | composition", "argument | prose", "college | writing"),
    },
    {
        "match_all": ["ethic"],
        "equivalency_group": "applied_ethics",
        "levels": ("humanities | thought", "philosophy | ethics", "moral | reasoning", "applied | ethics"),
    },
    {
        "match_all": ["machine", "learning"],
        "equivalency_group": "machine_learning",
        "levels": ("computing | data", "intelligent | systems", "predictive | modeling", "machine | learning"),
    },
    {
        "match_all": ["network"],
        "equivalency_group": "computer_networks",
        "levels": ("computing | data", "systems | infrastructure", "network | communication", "computer | networks"),
    },
]


def normalize_path(text: str) -> str:
    text = str(text).strip()
    text = text.replace(" / ", " > ").replace(" :: ", " > ")
    return " > ".join(part.strip() for part in text.split(" > ") if part.strip())


def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace("&", " and ")
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\b1\b", " one ", text)
    replacements = {
        "fundamentals": "foundation",
        "fundamental": "foundation",
        "introductory": "intro",
        "introduction": "intro",
        "coding": "programming",
        "program": "programming",
        "structures": "structure",
        "algorithms": "algorithm",
        "databases": "database",
        "systems": "system",
        "statistics": "statistic",
        "genes": "genetic",
        "genetics": "genetic",
        "ethics": "ethic",
        "composition": "writing",
        "expository": "academic",
        "practical": "applied",
        "society": "applied",
        "communication": "network",
        "reasoning": "proof",
        "matrix": "linear",
        "networks": "network",
    }
    words = []
    for token in text.split():
        words.append(replacements.get(token, token))
    return " ".join(words)


def rule_matches(text: str, rule: dict) -> bool:
    tokens = set(text.split())
    if "match_all" in rule and not all(term in tokens for term in rule["match_all"]):
        return False
    if "match_none" in rule and any(term in tokens for term in rule["match_none"]):
        return False
    if "match_any" in rule:
        if not any(all(term in tokens for term in option) for option in rule["match_any"]):
            return False
    return True


def assign_subjects(normalized_title: str, normalized_path: str) -> tuple[str, tuple[str, str, str, str]]:
    combined = f"{normalized_title} {normalized_path}"
    for rule in RULES:
        if rule_matches(combined, rule):
            return rule["equivalency_group"], rule["levels"]
    raise ValueError(f"No rule matched: {combined}")


def load_northbridge() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "northbridge_course_catalog.csv")
    return pd.DataFrame(
        {
            "university": "northbridge",
            "course_code": df["course_code"],
            "course_title": df["course_title"],
            "source_course_path": df["catalog_path"],
            "credit_units": df["credits"],
        }
    )


def load_redwood() -> pd.DataFrame:
    rows = []
    with open(DATA_DIR / "redwood_school_catalog.jsonl", "r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            rows.append(
                {
                    "university": "redwood",
                    "course_code": payload["course_id"],
                    "course_title": payload["title"],
                    "source_course_path": payload["academic_path"],
                    "credit_units": payload["units"],
                }
            )
    return pd.DataFrame(rows)


def load_lakeside() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "lakeside_program_catalog.tsv", sep="\t")
    return pd.DataFrame(
        {
            "university": "lakeside",
            "course_code": df["catalog_number"],
            "course_title": df["course_name"],
            "source_course_path": df["curriculum_branch"],
            "credit_units": df["credit_hours"],
        }
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mapping = pd.concat([load_northbridge(), load_redwood(), load_lakeside()], ignore_index=True)
    mapping["source_course_path"] = mapping["source_course_path"].map(normalize_path)
    mapping["source_depth"] = mapping["source_course_path"].str.count(" > ") + 1
    mapping["normalized_course_title"] = mapping["course_title"].map(normalize_text)

    groups = mapping.apply(
        lambda row: assign_subjects(row["normalized_course_title"], normalize_text(row["source_course_path"])),
        axis=1,
        result_type="expand",
    )
    mapping["equivalency_group"] = groups[0]
    levels = pd.DataFrame(groups[1].tolist(), columns=["subject_area_l1", "subject_area_l2", "subject_area_l3", "subject_area_l4"])
    mapping = pd.concat([mapping, levels], axis=1)

    mapping = mapping[
        [
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
    ].sort_values(["subject_area_l1", "subject_area_l2", "equivalency_group", "university"]).reset_index(drop=True)

    hierarchy = mapping[["subject_area_l1", "subject_area_l2", "subject_area_l3", "subject_area_l4"]].drop_duplicates().sort_values(
        ["subject_area_l1", "subject_area_l2", "subject_area_l3", "subject_area_l4"]
    ).reset_index(drop=True)

    summary = (
        mapping.groupby(
            ["equivalency_group", "subject_area_l1", "subject_area_l2", "subject_area_l3", "subject_area_l4"],
            as_index=False,
        )
        .agg(
            university_count=("university", "nunique"),
            course_count=("course_code", "count"),
            min_credit_units=("credit_units", "min"),
            max_credit_units=("credit_units", "max"),
        )
        .sort_values(["subject_area_l1", "subject_area_l2", "equivalency_group"])
        .reset_index(drop=True)
    )

    mapping.to_csv(OUTPUT_DIR / "course_transfer_mapping.csv", index=False)
    hierarchy.to_csv(OUTPUT_DIR / "subject_taxonomy_hierarchy.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "transfer_overlap_summary.csv", index=False)


if __name__ == "__main__":
    main()
PY

python3 /tmp/curriculum_transfer_solver.py
