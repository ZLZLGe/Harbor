import json
from pathlib import Path

import pytest

OUTPUT_FILE = Path("/root/duplicate_map.json")

EXPECTED_DUPLICATE_MAP = {
    "brown2020gpt3": ["Brown2020LM", "gpt3fewshot2020"],
    "hu2021lora": ["lora_llm_2021"],
    "lewis2020rag": ["lewis2020retrieval_augmented"],
}

UNIQUE_KEYS = {
    "kojima2022large",
    "ouyang2022training",
    "touvron2023llama",
    "wei2022chainthought",
}


def load_output():
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
    with OUTPUT_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


class TestOutputStructure:
    def test_output_exists(self):
        assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"

    def test_output_is_valid_json(self):
        with OUTPUT_FILE.open(encoding="utf-8") as handle:
            try:
                json.load(handle)
            except json.JSONDecodeError as exc:
                pytest.fail(f"Output is not valid JSON: {exc}")

    def test_required_top_level_key(self):
        data = load_output()
        assert "duplicate_map" in data, "Missing required key: duplicate_map"
        assert isinstance(data["duplicate_map"], dict), "duplicate_map must be a JSON object"


class TestDuplicateResolution:
    def test_exact_expected_mapping(self):
        data = load_output()
        assert data["duplicate_map"] == EXPECTED_DUPLICATE_MAP, "Duplicate mapping does not match expected canonical resolution"

    def test_canonical_keys_sorted(self):
        data = load_output()
        keys = list(data["duplicate_map"].keys())
        assert keys == sorted(keys), "Canonical keys must be sorted in ascending order"

    def test_each_merged_key_array_sorted(self):
        data = load_output()
        for canonical, merged_keys in data["duplicate_map"].items():
            assert merged_keys == sorted(merged_keys), f"Merged keys for {canonical} must be sorted"

    def test_canonical_key_not_repeated_in_own_cluster(self):
        data = load_output()
        for canonical, merged_keys in data["duplicate_map"].items():
            assert canonical not in merged_keys, f"Canonical key {canonical} must not appear in its own merged list"


class TestNoFalsePositives:
    def test_unique_keys_not_promoted_to_canonical(self):
        data = load_output()
        assert UNIQUE_KEYS.isdisjoint(data["duplicate_map"].keys()), "Unique records must not appear as canonical duplicate groups"

    def test_unique_keys_not_listed_as_duplicates(self):
        data = load_output()
        flattened = {key for merged_keys in data["duplicate_map"].values() for key in merged_keys}
        assert UNIQUE_KEYS.isdisjoint(flattened), "Unique records must not appear in merged duplicate lists"

    def test_duplicate_group_count(self):
        data = load_output()
        assert len(data["duplicate_map"]) == 3, "Expected exactly three duplicate clusters"
