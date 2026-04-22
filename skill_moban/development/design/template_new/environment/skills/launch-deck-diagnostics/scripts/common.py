from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
DECK_HTML_PATH = OUTPUT_ROOT / "deck" / "index.html"
SUBMISSION_PATH = OUTPUT_ROOT / "deck_submission.json"
RECEIPT_PATH = OUTPUT_ROOT / "deck_receipt.json"
INTERNAL_REVIEW_DRAFT_PATH = WORKSPACE_ROOT / "drafts" / "internal_review_draft.html"
QA_URL = os.environ.get("DECK_QA_URL", "http://127.0.0.1:8364")
SERVICE_LAUNCHER_PATH = Path(os.environ.get("RENDER_QA_LAUNCHER_PATH", "/usr/local/bin/render-qa-launcher"))
SERVICE_LOG_PATH = Path("/tmp/render-qa-skill.log")
CHROMIUM_EXECUTABLE_PATH = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/usr/bin/chromium")
REQUIRED_ROLES = [
    "cover",
    "kpi-overview",
    "comparison",
    "evidence",
    "journey-diagram",
    "risks-next-steps",
]
VIEWPORTS = [
    {"name": "primary", "width": 1440, "height": 900},
    {"name": "secondary", "width": 1280, "height": 720},
]


def load_html() -> str:
    return DECK_HTML_PATH.read_text(encoding="utf-8")


def load_soup() -> BeautifulSoup:
    return BeautifulSoup(load_html(), "html.parser")


def visible_text(node: Any) -> str:
    return " ".join(node.stripped_strings)


def collect_slides(soup: BeautifulSoup) -> list[Any]:
    return soup.select("[data-slide-role][data-slide-index]")


def collect_external_urls(html: str) -> list[str]:
    urls = re.findall(r"""(?:(?:src|href)=["']([^"']+)["']|url\(([^)]+)\))""", html, flags=re.IGNORECASE)
    found: list[str] = []
    for left, right in urls:
        candidate = (left or right).strip().strip("'\"")
        if candidate.lower().startswith(("http://", "https://", "//")):
            found.append(candidate)
    return found


def infer_slide_manifest_from_html() -> list[dict[str, Any]]:
    soup = load_soup()
    slides = collect_slides(soup)
    manifest: list[dict[str, Any]] = []
    for expected_index, slide in enumerate(slides):
        title_node = slide.find(["h1", "h2", "h3"])
        source_refs = []
        for tag in slide.select("[data-source-ref]"):
            ref = tag.get("data-source-ref", "").strip()
            if ref:
                source_refs.append(ref)
        manifest.append(
            {
                "index": expected_index,
                "role": slide.get("data-slide-role", "").strip(),
                "title": visible_text(title_node) if title_node else "",
                "source_refs": source_refs,
            }
        )
    return manifest


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def get_manifest() -> dict[str, Any]:
    ensure_service()
    response = requests.get(f"{QA_URL}/manifest", timeout=10)
    response.raise_for_status()
    return response.json()


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
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{QA_URL}/manifest", timeout=3)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
            continue
        time.sleep(0.5)

    if launcher_proc is not None:
        launcher_proc.terminate()

    log_tail = ""
    if SERVICE_LOG_PATH.exists():
        lines = SERVICE_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            log_tail = " | launcher log tail: " + " || ".join(lines[-20:])

    raise RuntimeError(f"render QA service did not become ready{log_tail}")
