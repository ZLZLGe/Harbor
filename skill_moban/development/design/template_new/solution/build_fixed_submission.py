#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
DECK_HTML_PATH = OUTPUT_ROOT / "deck" / "index.html"
SUBMISSION_PATH = OUTPUT_ROOT / "deck_submission.json"
RECEIPT_PATH = OUTPUT_ROOT / "deck_receipt.json"
QA_URL = os.environ.get("DECK_QA_URL", "http://127.0.0.1:8364")
SERVICE_LAUNCHER_PATH = Path(os.environ.get("RENDER_QA_LAUNCHER_PATH", "/usr/local/bin/render-qa-launcher"))
SERVICE_LOG_PATH = Path("/tmp/render-qa-solution.log")


def ensure_service(timeout_sec: float = 20.0) -> None:
    launcher_proc = None
    try:
        response = requests.get(f"{QA_URL}/manifest", timeout=3)
        if response.status_code == 200:
            return
    except requests.RequestException:
        pass

    if SERVICE_LAUNCHER_PATH.exists():
        launcher_proc = subprocess.Popen(
            [str(SERVICE_LAUNCHER_PATH)],
            stdout=open(SERVICE_LOG_PATH, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )

    deadline = time.monotonic() + timeout_sec
    last_error = "unknown error"
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{QA_URL}/manifest", timeout=3)
            if response.status_code == 200:
                return
            last_error = f"manifest returned {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.5)

    if launcher_proc is not None:
        launcher_proc.terminate()

    log_tail = ""
    if SERVICE_LOG_PATH.exists():
        lines = SERVICE_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            log_tail = " | launcher log tail: " + " || ".join(lines[-20:])

    raise RuntimeError(f"render QA service did not become ready: {last_error}{log_tail}")


def main() -> None:
    ensure_service()
    submission = {
        "job_id": "atlasflow-launch-storyboard-fixed-solution",
        "entry_html": "/app/output/deck/index.html",
        "slide_count": 6,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "slides": [
            {
                "index": 0,
                "role": "cover",
                "title": "AtlasFlow Review gives launch teams one visible approval path.",
                "source_refs": [
                    "/app/workspace/brief/creative_brief.md",
                    "/app/workspace/data/customer_quotes.json",
                    "/app/workspace/mirror/site/index.html",
                ],
            },
            {
                "index": 1,
                "role": "kpi-overview",
                "title": "Readiness signals point to faster, steadier launch review.",
                "source_refs": [
                    "/app/workspace/data/weekly_kpis.csv",
                    "/app/workspace/brief/creative_brief.md",
                ],
            },
            {
                "index": 2,
                "role": "comparison",
                "title": "AtlasFlow Review is strongest where review routing and sign-off need structure.",
                "source_refs": [
                    "/app/workspace/data/feature_matrix.csv",
                    "/app/workspace/brief/creative_brief.md",
                ],
            },
            {
                "index": 3,
                "role": "evidence",
                "title": "Customer evidence is strongest on visibility, accountability, and launch readiness.",
                "source_refs": [
                    "/app/workspace/data/customer_quotes.json",
                    "/app/workspace/brief/creative_brief.md",
                ],
            },
            {
                "index": 4,
                "role": "journey-diagram",
                "title": "The intended workflow moves from intake to sign-off with explicit rework loops.",
                "source_refs": [
                    "/app/workspace/data/user_journey.json",
                    "/app/workspace/brief/creative_brief.md",
                ],
            },
            {
                "index": 5,
                "role": "risks-next-steps",
                "title": "Launch confidence is real, but external review and multilingual workflows remain out of scope.",
                "source_refs": [
                    "/app/workspace/brief/creative_brief.md",
                    "/app/workspace/data/customer_quotes.json",
                    "/app/workspace/specs/deck_contract.md",
                ],
            },
        ],
    }
    SUBMISSION_PATH.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")

    response = requests.post(f"{QA_URL}/validate", json=submission, timeout=30)
    response.raise_for_status()
    RECEIPT_PATH.write_text(json.dumps(response.json(), indent=2) + "\n", encoding="utf-8")
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
