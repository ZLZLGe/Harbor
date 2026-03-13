import json
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/fake_citation_titles.json")

EXPECTED_TITLES = [
    "Federated Evidence Retrieval for Living Systematic Reviews",
    "Handbook of NeuroSymbolic Screening Pipelines",
    "Probabilistic Evidence Synthesis with LLM-Generated Trial Embeddings",
    "Zero-Shot Meta-Synthesis for Clinical Trial Evidence Screening",
]

REAL_TITLES = [
    "Large Language Models Encode Clinical Knowledge",
    "LoRA: Low-Rank Adaptation of Large Language Models",
    "PRISMA 2020 statement: an updated guideline for reporting systematic reviews",
    "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    "The Handbook of Research Synthesis and Meta-Analysis",
]


def normalize(title: str) -> str:
    return " ".join(title.split()).lower()


def load_output():
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        return json.load(f)


class TestOutputStructure:
    def test_output_exists(self):
        assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"

    def test_output_is_valid_json(self):
        with OUTPUT_FILE.open(encoding="utf-8") as f:
            try:
                json.load(f)
            except json.JSONDecodeError as exc:
                pytest.fail(f"Output file is not valid JSON: {exc}")

    def test_output_is_string_list(self):
        data = load_output()
        assert isinstance(data, list), "Expected top-level JSON array"
        assert all(isinstance(item, str) for item in data), "All items must be strings"


class TestSuspiciousTitles:
    def test_exact_titles(self):
        data = load_output()
        assert data == EXPECTED_TITLES, "Suspicious titles do not match expected sorted list"

    def test_count(self):
        data = load_output()
        assert len(data) == 4, f"Expected 4 suspicious titles, found {len(data)}"

    def test_sorted(self):
        data = load_output()
        assert data == sorted(data), "Titles must be sorted alphabetically"

    def test_titles_are_cleaned(self):
        data = load_output()
        for title in data:
            assert "{" not in title and "}" not in title, f"Unclean title found: {title}"
            assert "\\" not in title, f"Unclean title found: {title}"

    def test_real_titles_not_flagged(self):
        detected = {normalize(title) for title in load_output()}
        for real_title in REAL_TITLES:
            assert normalize(real_title) not in detected, f"Real title was incorrectly flagged: {real_title}"
