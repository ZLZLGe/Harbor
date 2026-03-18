import json
import os
from pathlib import Path

import pytest

ANSWER_FILE = Path(os.environ.get("ASSET_RESOLUTION_OUTPUT", "/root/asset_resolution.json"))

EXPECTED_PAYLOAD = {
    "resolved_records": [
        {
            "canonical_id": "alphafold2021",
            "title": "Highly Accurate Protein Structure Prediction with AlphaFold",
            "year": 2021,
            "matched_inputs": [
                "10.1038/s41586-021-03819-2",
                "https://www.nature.com/articles/s41586-021-03819-2",
            ],
            "identifiers": {
                "doi": "10.1038/s41586-021-03819-2",
                "pmid": "34265844",
                "arxiv": None,
                "url": "https://www.nature.com/articles/s41586-021-03819-2",
            },
        },
        {
            "canonical_id": "attention2017",
            "title": "Attention Is All You Need",
            "year": 2017,
            "matched_inputs": ["arXiv:1706.03762"],
            "identifiers": {
                "doi": None,
                "pmid": None,
                "arxiv": "1706.03762",
                "url": "https://arxiv.org/abs/1706.03762",
            },
        },
        {
            "canonical_id": "bert2018",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
            "year": 2018,
            "matched_inputs": ["https://arxiv.org/abs/1810.04805"],
            "identifiers": {
                "doi": None,
                "pmid": None,
                "arxiv": "1810.04805",
                "url": "https://arxiv.org/abs/1810.04805",
            },
        },
        {
            "canonical_id": "semaglutide2021",
            "title": "Effect of Continued Weekly Subcutaneous Semaglutide vs Placebo on Weight Loss Maintenance in Adults With Overweight or Obesity: The STEP 4 Randomized Clinical Trial",
            "year": 2021,
            "matched_inputs": ["PMID: 33755727"],
            "identifiers": {
                "doi": "10.1001/jama.2021.3224",
                "pmid": "33755727",
                "arxiv": None,
                "url": "https://pubmed.ncbi.nlm.nih.gov/33755727/",
            },
        },
        {
            "canonical_id": "tirzepatide2022",
            "title": "Tirzepatide Once Weekly for the Treatment of Obesity",
            "year": 2022,
            "matched_inputs": [
                "https://pubmed.ncbi.nlm.nih.gov/35658024/",
                "https://doi.org/10.1056/NEJMoa2206038",
            ],
            "identifiers": {
                "doi": "10.1056/NEJMoa2206038",
                "pmid": "35658024",
                "arxiv": None,
                "url": "https://pubmed.ncbi.nlm.nih.gov/35658024/",
            },
        },
    ],
    "unverified_items": [
        {"input": "doi:10.9999/example.fake.2025.1", "reason": "no_matching_record"},
        {"input": "PMID 99999999", "reason": "no_matching_record"},
        {"input": "https://arxiv.org/abs/9999.99999", "reason": "no_matching_record"},
    ],
}


def load_answer():
    assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"
    with ANSWER_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


class TestOutputFile:
    def test_output_exists(self):
        assert ANSWER_FILE.exists(), f"Missing output file: {ANSWER_FILE}"

    def test_output_is_valid_json(self):
        data = load_answer()
        assert isinstance(data, dict)

    def test_top_level_keys_are_exact(self):
        data = load_answer()
        assert sorted(data.keys()) == ["resolved_records", "unverified_items"]


class TestResolvedRecords:
    def test_exact_resolved_payload(self):
        data = load_answer()
        assert data["resolved_records"] == EXPECTED_PAYLOAD["resolved_records"]

    def test_resolved_record_order(self):
        data = load_answer()
        actual_order = [item["canonical_id"] for item in data["resolved_records"]]
        expected_order = [item["canonical_id"] for item in EXPECTED_PAYLOAD["resolved_records"]]
        assert actual_order == expected_order

    @pytest.mark.parametrize(
        "canonical_id,expected_inputs",
        [
            ("alphafold2021", ["10.1038/s41586-021-03819-2", "https://www.nature.com/articles/s41586-021-03819-2"]),
            ("attention2017", ["arXiv:1706.03762"]),
            ("bert2018", ["https://arxiv.org/abs/1810.04805"]),
            ("semaglutide2021", ["PMID: 33755727"]),
            ("tirzepatide2022", ["https://pubmed.ncbi.nlm.nih.gov/35658024/", "https://doi.org/10.1056/NEJMoa2206038"]),
        ],
    )
    def test_matched_inputs_are_preserved(self, canonical_id, expected_inputs):
        data = load_answer()
        record = next(item for item in data["resolved_records"] if item["canonical_id"] == canonical_id)
        assert record["matched_inputs"] == expected_inputs

    def test_identifier_keys_are_complete(self):
        data = load_answer()
        for record in data["resolved_records"]:
            assert list(record["identifiers"].keys()) == ["doi", "pmid", "arxiv", "url"]


class TestUnverifiedItems:
    def test_exact_unverified_payload(self):
        data = load_answer()
        assert data["unverified_items"] == EXPECTED_PAYLOAD["unverified_items"]

    def test_unverified_reason_is_consistent(self):
        data = load_answer()
        for item in data["unverified_items"]:
            assert item["reason"] == "no_matching_record"


class TestCoverage:
    def test_every_input_accounted_for_once(self):
        data = load_answer()
        seen_inputs = []
        for record in data["resolved_records"]:
            seen_inputs.extend(record["matched_inputs"])
        seen_inputs.extend(item["input"] for item in data["unverified_items"])

        assert seen_inputs == [
            "10.1038/s41586-021-03819-2",
            "https://www.nature.com/articles/s41586-021-03819-2",
            "arXiv:1706.03762",
            "https://arxiv.org/abs/1810.04805",
            "PMID: 33755727",
            "https://pubmed.ncbi.nlm.nih.gov/35658024/",
            "https://doi.org/10.1056/NEJMoa2206038",
            "doi:10.9999/example.fake.2025.1",
            "PMID 99999999",
            "https://arxiv.org/abs/9999.99999",
        ]

    def test_no_empty_arrays(self):
        data = load_answer()
        assert data["resolved_records"]
        assert data["unverified_items"]
