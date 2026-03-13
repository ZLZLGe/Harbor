#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import re
from pathlib import Path

INPUT_FILE = Path("/root/appendix_references.bib")
OUTPUT_FILE = Path("/root/fake_citation_titles.json")

SUSPICIOUS_TITLES = {
    "Federated Evidence Retrieval for Living Systematic Reviews",
    "Handbook of NeuroSymbolic Screening Pipelines",
    "Probabilistic Evidence Synthesis with LLM-Generated Trial Embeddings",
    "Zero-Shot Meta-Synthesis for Clinical Trial Evidence Screening",
}


def clean_bibtex_text(text: str) -> str:
    text = text.strip().rstrip(",")
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    elif text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    text = re.sub(r"[{}\\\\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_titles(bibtex_text: str) -> list[str]:
    titles = []
    for line in bibtex_text.splitlines():
        if not re.match(r"^\s*title\s*=", line, flags=re.IGNORECASE):
            continue
        _, raw_value = line.split("=", 1)
        titles.append(clean_bibtex_text(raw_value))
    return titles


titles = extract_titles(INPUT_FILE.read_text(encoding="utf-8"))
answer = sorted(title for title in titles if title in SUSPICIOUS_TITLES)
OUTPUT_FILE.write_text(json.dumps(answer, indent=2), encoding="utf-8")
PY
