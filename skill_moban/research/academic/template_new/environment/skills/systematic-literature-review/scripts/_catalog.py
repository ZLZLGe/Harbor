#!/usr/bin/env python3
import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "review_catalog.json"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
RECORDS_BY_ID = {record["study_id"]: record for record in CATALOG["records"]}


def load_record(study_id: str) -> dict:
    try:
        return RECORDS_BY_ID[study_id]
    except KeyError as exc:
        raise KeyError(f"Study {study_id} is not present in the bundled review catalog.") from exc


def load_records(study_ids: list[str]) -> dict[str, dict]:
    return {study_id: load_record(study_id) for study_id in study_ids}
