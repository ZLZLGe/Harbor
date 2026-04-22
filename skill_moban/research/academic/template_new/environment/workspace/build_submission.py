#!/usr/bin/env python3
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import bibtexparser
import requests


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", str(Path(__file__).resolve().parent)))
OUTPUT_PATH = Path(os.environ.get("SUBMISSION_OUTPUT_PATH", "/app/output/submission_package.json"))
API_BASE = os.environ.get("ACADEMIC_API_URL", "http://127.0.0.1:8123")
SERVICE_CANDIDATES = [
    Path("/services/academic-api/server"),
    Path("/services/academic-api/server.py"),
    Path("/opt/academic-api/server.py"),
]


def load_included_studies() -> list[dict[str, str]]:
    path = WORKSPACE / "included_studies.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized_rows = []
    for row in rows:
        cleaned = {key: (value or "").strip() for key, value in row.items()}
        if cleaned.get("duration_weeks"):
            cleaned["duration_weeks"] = str(int(cleaned["duration_weeks"]))
        normalized_rows.append(cleaned)
    return normalized_rows


def load_references() -> list[dict]:
    path = WORKSPACE / "references.bib"
    with path.open("r", encoding="utf-8") as handle:
        database = bibtexparser.load(handle)
    return database.entries


def load_summary() -> str:
    return (WORKSPACE / "summary.md").read_text(encoding="utf-8")


def request_json(method: str, route: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f"{API_BASE}{route}"
    response = requests.request(method, url, json=payload, timeout=30)
    response.raise_for_status()
    return response.status_code, response.json()


def _service_available() -> bool:
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def ensure_service() -> None:
    if _service_available():
        return

    for candidate in SERVICE_CANDIDATES:
        if not candidate.exists():
            continue
        command = [str(candidate)]
        if candidate.suffix == ".py":
            command = [sys.executable, str(candidate)]
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(0.5)
            if _service_available():
                return
        break

    raise RuntimeError(
        "Local review validation service is unavailable. "
        "Start the academic API before building the submission package."
    )


def main() -> int:
    included_studies = load_included_studies()
    references = load_references()
    summary_text = load_summary()

    trace: dict[str, object] = {"base_url": API_BASE}
    try:
        ensure_service()
        health_status, health_payload = request_json("GET", "/health")
        trace["health"] = {"status_code": health_status, "snapshot_id": health_payload["snapshot_id"]}

        included_status, included_validation = request_json(
            "POST",
            "/validate/included-studies",
            {"included_studies": included_studies},
        )
        trace["included_studies"] = {
            "status_code": included_status,
            "is_valid": bool(included_validation["is_valid"]),
            "submitted_count": included_validation.get("submitted_count"),
        }

        included_ids = [row["study_id"] for row in included_studies]
        references_status, references_validation = request_json(
            "POST",
            "/validate/references",
            {"references": references, "included_study_ids": included_ids},
        )
        trace["references"] = {
            "status_code": references_status,
            "is_valid": bool(references_validation["is_valid"]),
            "submitted_reference_count": references_validation.get("submitted_reference_count"),
            "matched_reference_count": references_validation.get("matched_reference_count"),
        }

        summary_status, summary_validation = request_json(
            "POST",
            "/validate/summary",
            {"summary": summary_text, "included_study_ids": included_ids},
        )
        trace["summary"] = {
            "status_code": summary_status,
            "is_valid": bool(summary_validation["is_valid"]),
        }
    except (requests.RequestException, RuntimeError):
        print(
            "Submission package validation could not reach the local review validation service.",
            file=sys.stderr,
        )
        return 2

    included_ids = [row["study_id"] for row in included_studies]

    screening_passed = bool(included_validation["is_valid"])
    bibliography_passed = bool(references_validation["is_valid"])
    summary_passed = bool(summary_validation["is_valid"])
    validation_passed = screening_passed and bibliography_passed and summary_passed
    package = {
        "snapshot_id": health_payload["snapshot_id"],
        "validation_passed": validation_passed,
        "validation_details": {
            "included_studies": screening_passed,
            "references": bibliography_passed,
            "summary": summary_passed,
        },
        "api_trace": trace,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if validation_passed:
        print("Submission package validation passed.")
        return 0

    print(
        "Validation details: "
        f"included_studies={screening_passed}, "
        f"references={bibliography_passed}, "
        f"summary={summary_passed}",
        file=sys.stderr,
    )
    print("Submission package validation failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
