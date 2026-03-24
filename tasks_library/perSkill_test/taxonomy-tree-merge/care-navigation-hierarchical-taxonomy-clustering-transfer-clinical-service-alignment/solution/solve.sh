#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os
import re
from pathlib import Path

import pandas as pd


DATA_DIR = Path(os.getenv("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_delimiters(text: str) -> str:
    text = str(text).strip()
    text = text.replace(" :: ", " > ")
    text = text.replace(" / ", " > ")
    text = re.sub(r"\s*>\s*", " > ", text)
    return text


def normalize_text(text: str) -> str:
    text = normalize_delimiters(text).lower()
    replacements = {
        "&": " and ",
        "-": " ",
        "ob ": " obstetric ",
        "ob clinic": "obstetric clinic",
        "low acuity": "minor",
        "same day clinic partner": "same day office",
        "walk in": "walkin",
        "follow up": "followup",
        "pre op": "perioperative",
        "telepsychiatry": "psychiatry",
        "womens": "women",
        "school age": "school age",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9> ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*>\s*", " > ", text)
    return text


UNIFIED_PATHS = {
    "urgent_office": (
        "adult | primary",
        "acute | access",
        "urgent | same day",
        "evaluation | visit",
        "office | care",
    ),
    "urgent_virtual": (
        "adult | primary",
        "acute | access",
        "urgent | same day",
        "evaluation | visit",
        "virtual | care",
    ),
    "annual_wellness": (
        "adult | primary",
        "preventive | care",
        "annual | wellness",
        "exam | planning",
        "office | care",
    ),
    "diabetes_followup": (
        "adult | primary",
        "chronic | care",
        "diabetes | support",
        "followup | review",
        "hybrid | care",
    ),
    "well_child": (
        "pediatric | care",
        "preventive | care",
        "well | child",
        "school | age",
        "office | care",
    ),
    "peds_fever_virtual": (
        "pediatric | care",
        "acute | access",
        "fever | cough",
        "rapid | visit",
        "virtual | care",
    ),
    "prenatal_routine": (
        "women | maternal",
        "prenatal | care",
        "routine | obstetric",
        "trimester | visit",
        "office | care",
    ),
    "prenatal_ultrasound": (
        "women | maternal",
        "prenatal | imaging",
        "fetal | ultrasound",
        "anatomy | review",
        "imaging | service",
    ),
    "mammography": (
        "women | wellness",
        "breast | imaging",
        "screening | mammography",
        "routine | screen",
        "imaging | service",
    ),
    "ortho_consult": (
        "orthopedic | care",
        "joint | evaluation",
        "knee | pain",
        "specialist | consult",
        "office | care",
    ),
    "knee_replacement": (
        "orthopedic | care",
        "surgical | pathways",
        "knee | replacement",
        "perioperative | support",
        "procedure | service",
    ),
    "arrhythmia": (
        "cardiac | care",
        "specialty | clinic",
        "arrhythmia | review",
        "diagnostic | consult",
        "office | care",
    ),
    "cardiac_rehab": (
        "cardiac | care",
        "recovery | program",
        "cardiac | rehab",
        "monitored | exercise",
        "hybrid | care",
    ),
    "therapy": (
        "behavioral | health",
        "counseling | care",
        "individual | therapy",
        "anxiety | depression",
        "virtual | care",
    ),
    "med_management": (
        "behavioral | health",
        "psychiatry | care",
        "medication | management",
        "mood | anxiety",
        "virtual | care",
    ),
    "chemotherapy": (
        "oncology | services",
        "infusion | therapy",
        "chemotherapy | care",
        "treatment | cycle",
        "infusion | service",
    ),
    "colonoscopy": (
        "digestive | care",
        "preventive | endoscopy",
        "colon | screening",
        "outpatient | procedure",
        "procedure | service",
    ),
    "sleep_study": (
        "diagnostics | sleep",
        "home | testing",
        "sleep | study",
        "result | review",
        "hybrid | care",
    ),
}


def classify_concept(text: str) -> str:
    if "fever and cough" in text or ("fever" in text and "cough" in text):
        return "peds_fever_virtual"
    if "minor" in text or "same day" in text or "on demand" in text:
        if "video" in text or "virtual" in text:
            return "urgent_virtual"
        return "urgent_office"
    if "annual" in text and ("wellness" in text or "physical" in text):
        return "annual_wellness"
    if "diabetes" in text:
        return "diabetes_followup"
    if "well child" in text or "school age" in text or "school age checkup" in text:
        return "well_child"
    if ("prenatal" in text or "maternity" in text) and ("routine" in text or "trimester" in text) and "ultrasound" not in text:
        return "prenatal_routine"
    if "ultrasound" in text or "anatomy scan" in text:
        return "prenatal_ultrasound"
    if "mammogram" in text or "mammography" in text:
        return "mammography"
    if "knee replacement" in text or "arthroplasty" in text:
        return "knee_replacement"
    if "knee" in text and ("consult" in text or "pain" in text):
        return "ortho_consult"
    if "arrhythmia" in text or "rhythm" in text:
        return "arrhythmia"
    if "cardiac rehab" in text or "rehabilitation" in text:
        return "cardiac_rehab"
    if "medication" in text and ("psychiatry" in text or "mood" in text):
        return "med_management"
    if "individual therapy" in text or "weekly session" in text or "anxiety depression" in text:
        return "therapy"
    if "chemotherapy" in text or "infusion" in text:
        return "chemotherapy"
    if "colonoscopy" in text or "colon screening" in text:
        return "colonoscopy"
    if "sleep study" in text or "sleep test" in text:
        return "sleep_study"
    raise ValueError(f"Unclassified path: {text}")


def load_hospital() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "hospital_group_services.csv")
    return pd.DataFrame(
        {
            "source_system": "hospital_group",
            "source_service_id": df["hospital_service_code"],
            "source_service_path": df["enterprise_service_line"].map(normalize_delimiters),
            "booking_surface": df["booking_surface"].str.lower(),
            "care_mode": df["care_mode"].str.lower(),
        }
    )


def load_payer() -> pd.DataFrame:
    rows = []
    with open(DATA_DIR / "payer_benefit_catalog.jsonl", "r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            rows.append(
                {
                    "source_system": "payer_catalog",
                    "source_service_id": item["benefit_code"],
                    "source_service_path": normalize_delimiters(item["benefit_hierarchy"]),
                    "booking_surface": str(item["entry_point"]).lower(),
                    "care_mode": str(item["setting"]).lower(),
                }
            )
    return pd.DataFrame(rows)


def load_telehealth() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "telehealth_visit_directory.tsv", sep="\t")
    return pd.DataFrame(
        {
            "source_system": "telehealth_platform",
            "source_service_id": df["visit_id"],
            "source_service_path": df["visit_tree"].map(normalize_delimiters),
            "booking_surface": df["intake_channel"].str.lower(),
            "care_mode": df["modality"].str.lower(),
        }
    )


mapping = pd.concat([load_hospital(), load_payer(), load_telehealth()], ignore_index=True)
mapping["normalized_service_path"] = mapping["source_service_path"].map(normalize_text)
mapping["source_depth"] = mapping["source_service_path"].str.count(" > ") + 1
mapping["concept"] = mapping["normalized_service_path"].map(classify_concept)

for value in sorted(mapping["care_mode"].unique()):
    if value not in {"in_person", "virtual", "hybrid", "ancillary"}:
        raise ValueError(f"Unexpected care_mode: {value}")

for level in range(1, 6):
    mapping[f"unified_service_l{level}"] = mapping["concept"].map(lambda key: UNIFIED_PATHS[key][level - 1])

mapping = mapping[
    [
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
].sort_values(["unified_service_l1", "unified_service_l2", "source_system", "source_service_id"]).reset_index(drop=True)

hierarchy_cols = [f"unified_service_l{i}" for i in range(1, 6)]

hierarchy = mapping[hierarchy_cols].drop_duplicates().sort_values(hierarchy_cols).reset_index(drop=True)

summary = (
    mapping.groupby(hierarchy_cols, as_index=False)
    .agg(
        source_system_count=("source_system", "nunique"),
        booking_surface_count=("booking_surface", "nunique"),
        in_person_count=("care_mode", lambda s: int((s == "in_person").sum())),
        virtual_count=("care_mode", lambda s: int((s == "virtual").sum())),
        hybrid_count=("care_mode", lambda s: int((s == "hybrid").sum())),
        ancillary_count=("care_mode", lambda s: int((s == "ancillary").sum())),
    )
    .sort_values(hierarchy_cols)
    .reset_index(drop=True)
)

mapping.to_csv(OUTPUT_DIR / "clinical_service_crosswalk.csv", index=False)
hierarchy.to_csv(OUTPUT_DIR / "clinical_taxonomy_hierarchy.csv", index=False)
summary.to_csv(OUTPUT_DIR / "care_navigation_summary.csv", index=False)
PY
