from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import requests


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
TESTS_ROOT = Path(os.environ.get("TESTS_ROOT", "/tests"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"
OUTPUT_ROOT = TASK_ROOT / "output"
DECK_ROOT = OUTPUT_ROOT / "deck"
DECK_HTML_PATH = DECK_ROOT / "index.html"
SUBMISSION_PATH = OUTPUT_ROOT / "deck_submission.json"
RECEIPT_PATH = OUTPUT_ROOT / "deck_receipt.json"

QA_URL = os.environ.get("DECK_QA_URL", "http://127.0.0.1:8364")
QA_TRACE_PATH = Path("/tmp/launch_deck_qa_trace.jsonl")
LAST_VALIDATE_PATH = Path("/tmp/launch_deck_last_validate.json")
SERVICE_LAUNCHER_PATH = Path(os.environ.get("RENDER_QA_LAUNCHER_PATH", "/usr/local/bin/render-qa-launcher"))
SERVICE_LOG_PATH = Path("/tmp/render-qa-test.log")

def resolve_task_path(path_str: str) -> Path:
    if path_str.startswith("/app/"):
        return TASK_ROOT / path_str.removeprefix("/app/")
    if path_str == "/app":
        return TASK_ROOT
    return Path(path_str)


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
    last_error: str | None = None

    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{QA_URL}/manifest", timeout=3)
            if response.status_code == 200:
                return
            last_error = f"manifest returned status {response.status_code}"
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

    raise AssertionError(f"deck QA service did not become ready: {last_error or 'unknown error'}{log_tail}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_trace_events(path: Path = QA_TRACE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def canonical_json_sha(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def protected_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def failure_count(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    if value is None:
        return 0
    raise AssertionError(f"Unsupported failure payload: {value!r}")


def html_text() -> str:
    return DECK_HTML_PATH.read_text(encoding="utf-8")


def collect_external_urls(html: str) -> list[str]:
    urls = re.findall(r"""(?:(?:src|href)=["']([^"']+)["']|url\(([^)]+)\))""", html, flags=re.IGNORECASE)
    flattened: list[str] = []
    for left, right in urls:
        candidate = (left or right).strip().strip("'\"")
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered.startswith(("http://", "https://", "//")):
            flattened.append(candidate)
    return flattened


def assert_allowed_source_ref(ref: str) -> None:
    assert isinstance(ref, str) and ref.startswith("/app/workspace/"), f"Invalid source ref: {ref!r}"
    assert resolve_task_path(ref).exists(), f"Missing referenced source path: {ref}"


def assert_slide_payload(slide: dict[str, Any], index: int) -> None:
    assert isinstance(slide, dict), f"slide {index} is not a JSON object"
    if "index" in slide:
        assert slide["index"] == index
    if "role" in slide:
        assert isinstance(slide["role"], str) and slide["role"]
    if "title" in slide:
        assert isinstance(slide["title"], str) and slide["title"].strip()
    if "source_refs" in slide:
        assert isinstance(slide["source_refs"], list)
        for ref in slide["source_refs"]:
            assert_allowed_source_ref(ref)
