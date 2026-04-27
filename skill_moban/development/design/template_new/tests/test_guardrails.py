from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from conftest import read_output, soup, visible_text


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_protected_inputs_services_and_skill_files_are_unchanged() -> None:
    manifest_path = Path(os.environ.get("PROTECTED_HASHES_PATH", "/opt/frontend-slides-task/protected_hashes.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest
    for path_str, expected_hash in manifest.items():
        path = Path(path_str)
        assert path.exists(), path
        assert _sha256(path) == expected_hash, path


def test_b_not_an_image_or_hidden_text_deck() -> None:
    doc = soup()
    sections = doc.find_all("section")
    assert sections
    for index, section in enumerate(sections):
        section_text = re.sub(r"\s+", " ", section.get_text(" ", strip=True))
        assert len(section_text) >= 90, (index, section_text)
        images = section.find_all("img")
        assert len(images) <= 1, index
    html = read_output().lower()
    assert html.count("data:image/") <= 1
    hidden_text_patterns = [
        r"display\s*:\s*none[^}]{0,1600}(waterfront|north campus|harborloop)",
        r"visibility\s*:\s*hidden[^}]{0,1600}(waterfront|north campus|harborloop)",
    ]
    assert not any(re.search(pattern, html) for pattern in hidden_text_patterns)


def test_c_verifier_and_test_paths_are_not_referenced() -> None:
    html = read_output().lower()
    forbidden = [
        "/tests/",
        "test_outputs",
        "test_browser_behavior",
        "test_guardrails",
        "protected_hashes",
        "pytest",
        "reward.txt",
        "verifier",
    ]
    assert not any(token in html for token in forbidden)


def test_d_deck_uses_accessible_real_text_content() -> None:
    text = visible_text()
    assert len(text) > 1800
    doc = soup()
    assert doc.find("main") is not None or doc.find(attrs={"role": "main"}) is not None
    html = read_output().lower()
    assert doc.find(attrs={"aria-live": True}) is not None or "aria-current" in html or "/" in visible_text()
    headings = doc.find_all(re.compile("^h[1-3]$"))
    assert len(headings) >= 8
    structural_blocks = doc.find_all(["li", "article", "table", "svg"])
    assert len([item for item in structural_blocks if item.get_text(strip=True) or item.name == "svg"]) >= 3
