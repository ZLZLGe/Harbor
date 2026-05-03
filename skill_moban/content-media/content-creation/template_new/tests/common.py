from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path


SOURCE_ROOT = Path(os.environ.get("SOURCE_BUNDLE_ROOT", "/root/workspace/source_bundle"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/root/output"))
SERVICE_BASE_URL = os.environ.get("CONTENT_REVIEW_BASE_URL", "http://127.0.0.1:8147")

CAMPAIGN_SUMMARY_PATH = OUTPUT_ROOT / "campaign_summary.md"
X_THREAD_PATH = OUTPUT_ROOT / "x_thread.md"
LINKEDIN_PATH = OUTPUT_ROOT / "linkedin_post.md"
NEWSLETTER_PATH = OUTPUT_ROOT / "newsletter_draft.md"
SOURCE_MAP_PATH = OUTPUT_ROOT / "source_map.json"
GAPS_PATH = OUTPUT_ROOT / "publish_gaps.json"

SOURCE_INDEX = json.loads((SOURCE_ROOT / "source_index.json").read_text(encoding="utf-8"))
CONSTRAINTS = json.loads((SOURCE_ROOT / "campaign_constraints.json").read_text(encoding="utf-8"))
RED_FLAGS = [
    line.strip().lower()
    for line in (SOURCE_ROOT / "style_red_flags.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        headers={"X-Client": "verifier-main"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_source_ref(ref: str) -> tuple[str, int, int]:
    path_part, line_part = ref.split("#", 1)
    match = re.fullmatch(r"L(\d+)-L(\d+)", line_part)
    if not match:
        raise ValueError(f"invalid ref syntax: {ref}")
    start = int(match.group(1))
    end = int(match.group(2))
    return path_part, start, end


def get_ref_text(ref: str) -> str:
    rel_path, start, end = parse_source_ref(ref)
    file_path = SOURCE_ROOT / rel_path
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if start < 1 or end < start or end > len(lines):
        raise ValueError(f"ref out of range: {ref}")
    return "\n".join(lines[start - 1 : end])


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9'-]*", text.lower())


def unique_words(text: str) -> set[str]:
    return set(words(text))


def word_count(text: str) -> int:
    return len(words(text))


def thread_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"^\d+/", line.strip())]


def paragraph_count(text: str) -> int:
    return len([block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()])


def h2_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("## "))
