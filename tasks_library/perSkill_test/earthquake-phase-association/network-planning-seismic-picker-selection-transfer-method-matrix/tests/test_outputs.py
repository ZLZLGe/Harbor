import csv
import json
import os
import re
from pathlib import Path


DATA_DIR = Path(os.environ.get("METHOD_MATRIX_INPUT_DIR", "/root/planning_inputs"))
OUTPUT_FILE = Path(os.environ.get("METHOD_MATRIX_OUTPUT_FILE", "/root/method_matrix.json"))

EXPECTED_METHODS = {
    "city_accelerometer_watch": "sta_lta",
    "dam_regulatory_audit": "manual",
    "temp_nodal_aftershocks": "deep_learning",
    "template_swarm_archive": "template_matching",
}

REASON_CONSTRAINTS = {
    "city_accelerometer_watch": {
        "latency": ["seconds", "second", "fast", "real-time", "realtime", "quick"],
        "station type": ["accelerometer", "accelerometers", "strong-motion", "strong motion"],
        "compute limits": ["low compute", "minimal cpu", "minimal compute", "lightweight", "simple logic", "gateway"],
        "goal": ["felt shaking", "first-stage", "first stage", "trigger"],
    },
    "dam_regulatory_audit": {
        "review requirement": ["manual", "human review", "analyst", "review everything", "full review"],
        "false-positive tolerance": ["false positive", "false positives", "defensible", "regulatory", "audited", "compliance"],
        "timing": ["days", "daily"],
        "station mix": ["borehole", "broadband", "surface"],
    },
    "temp_nodal_aftershocks": {
        "deployment context": ["temporary", "temp", "nodal", "nodes", "aftershock", "post-mainshock", "post mainshock"],
        "template availability": ["no templates", "without templates", "no reusable templates", "no mature library", "template library"],
        "catalog goal": ["catalog", "continuous", "local aftershock", "complete"],
        "coverage gap": ["sparse", "rural gap", "permanent coverage"],
    },
    "template_swarm_archive": {
        "template availability": ["template", "templates", "repeating", "families", "known cluster"],
        "sensitivity goal": ["smallest", "sensitivity", "recurring events", "recurring"],
        "processing mode": ["offline", "overnight", "batch", "archive"],
        "deployment context": ["swarm", "geothermal"],
    },
}


def load_output():
    with OUTPUT_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_scenario_ids():
    with (DATA_DIR / "deployment_matrix.csv").open("r", encoding="utf-8", newline="") as fh:
        return sorted(row["scenario_id"] for row in csv.DictReader(fh))


def split_sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_top_level_schema():
    payload = load_output()
    assert set(payload.keys()) == {"matrix_version", "recommendations"}
    assert payload["matrix_version"] == "1.0"
    assert isinstance(payload["recommendations"], list)


def test_recommendations_cover_every_scenario_in_order():
    payload = load_output()
    recommendations = payload["recommendations"]
    expected_ids = load_scenario_ids()

    assert len(recommendations) == len(expected_ids)
    produced_ids = [item["scenario_id"] for item in recommendations]
    assert produced_ids == expected_ids

    for item in recommendations:
        assert set(item.keys()) == {"scenario_id", "recommended_method", "reason"}
        assert item["recommended_method"] in {"sta_lta", "deep_learning", "template_matching", "manual"}
        assert isinstance(item["reason"], str)


def test_expected_method_matrix():
    payload = load_output()
    produced = {item["scenario_id"]: item["recommended_method"] for item in payload["recommendations"]}
    assert produced == EXPECTED_METHODS
    assert set(produced.values()) == {"sta_lta", "deep_learning", "template_matching", "manual"}


def test_reasons_reference_concrete_constraints():
    payload = load_output()
    for item in payload["recommendations"]:
        reason = item["reason"].strip().lower()
        assert reason
        assert "\n" not in reason
        assert 1 <= len(split_sentences(item["reason"])) <= 2

        matched_constraints = [
            label
            for label, options in REASON_CONSTRAINTS[item["scenario_id"]].items()
            if any(option in reason for option in options)
        ]
        assert len(matched_constraints) >= 2, (
            f"reason for {item['scenario_id']} should mention at least two concrete scenario constraints: "
            f"{item['reason']}"
        )
