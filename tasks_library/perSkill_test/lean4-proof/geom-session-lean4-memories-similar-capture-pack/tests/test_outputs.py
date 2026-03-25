import json
from pathlib import Path


OUTPUT_PATH = Path("/app/artifacts/geom-session-memory-pack.json")


def load_output():
    assert OUTPUT_PATH.exists(), "Missing /app/artifacts/geom-session-memory-pack.json"
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def assert_evidence_list(items):
    assert isinstance(items, list) and items, "source_evidence must be a non-empty list"
    for item in items:
      assert isinstance(item, dict), "Each source_evidence item must be an object"
      assert isinstance(item.get("file"), str) and item["file"], "source_evidence.file must be a non-empty string"
      assert isinstance(item.get("quote_or_line_hint"), str) and item["quote_or_line_hint"], "source_evidence.quote_or_line_hint must be a non-empty string"


def test_top_level_contract():
    data = load_output()
    required = {
        "session_id",
        "source_files",
        "proof_patterns",
        "failed_approaches",
        "project_conventions",
        "reuse_advice",
    }
    assert required.issubset(data), f"Missing top-level keys: {required - set(data)}"
    assert isinstance(data["session_id"], str) and data["session_id"]
    assert isinstance(data["source_files"], list) and data["source_files"]
    assert isinstance(data["reuse_advice"], list) and len(data["reuse_advice"]) >= 2
    assert isinstance(data["proof_patterns"], list) and data["proof_patterns"]
    assert isinstance(data["failed_approaches"], list) and data["failed_approaches"]
    assert isinstance(data["project_conventions"], list) and data["project_conventions"]


def test_sources_cover_all_session_materials():
    data = load_output()
    expected = {
        "/app/session_assets/geom_bound_session.lean",
        "/app/session_assets/failed_attempts.md",
        "/app/session_assets/project_conventions.md",
    }
    assert expected.issubset(set(data["source_files"])), "source_files should list all provided session assets"


def test_proof_pattern_captures_successful_strategy():
    data = load_output()
    matched = False
    for pattern in data["proof_patterns"]:
        for key in ["name", "goal_shape", "strategy", "supporting_details", "source_evidence"]:
            assert key in pattern, f"proof pattern missing {key}"
        details = pattern["supporting_details"]
        assert isinstance(details, dict), "supporting_details must be an object"
        assert isinstance(details.get("tactics"), list), "supporting_details.tactics must be a list"
        assert isinstance(details.get("helper_lemmas"), list), "supporting_details.helper_lemmas must be a list"
        strategy_text = " ".join(
            [pattern["goal_shape"], pattern["strategy"], " ".join(details["tactics"]), " ".join(details["helper_lemmas"])]
        ).lower()
        if (
            "induction" in strategy_text
            and (("closed form" in strategy_text) or ("h_closed" in strategy_text))
            and (("linarith" in strategy_text) or ("positivity" in strategy_text))
        ):
            matched = True
        assert_evidence_list(pattern["source_evidence"])
    assert matched, "Need at least one proof pattern capturing the induction -> closed-form -> inequality strategy"


def test_failed_approach_is_grounded_and_actionable():
    data = load_output()
    matched = False
    for item in data["failed_approaches"]:
        for key in [
            "name",
            "attempted_step",
            "failure_signal",
            "why_it_failed",
            "better_direction",
            "source_evidence",
        ]:
            assert key in item, f"failed approach missing {key}"
            if key != "source_evidence":
                assert isinstance(item[key], str) and item[key], f"{key} must be a non-empty string"
        text = " ".join(
            [item["attempted_step"], item["failure_signal"], item["why_it_failed"], item["better_direction"]]
        ).lower()
        if (("linarith" in text) or ("simp" in text)) and (
            ("rewrite" in text) or ("induction" in text) or ("ring" in text)
        ):
            matched = True
        assert_evidence_list(item["source_evidence"])
    assert matched, "Need at least one failed approach tied to a provided dead end and a concrete better direction"


def test_project_convention_matches_note_style():
    data = load_output()
    found_supported_convention = False
    for item in data["project_conventions"]:
        for key in ["name", "rule", "reason", "source_evidence"]:
            assert key in item, f"project convention missing {key}"
            if key != "source_evidence":
                assert isinstance(item[key], str) and item[key], f"{key} must be a non-empty string"
        rule_text = f"{item['name']} {item['rule']} {item['reason']}".lower()
        if (
            (("relative" in rule_text) and ("path" in rule_text))
            or (("evidence" in rule_text) and ("file" in rule_text))
            or (("goal shape" in rule_text) and ("tactic" in rule_text))
            or (("helper" in rule_text) and ("tactic" in rule_text))
            or (("failure signal" in rule_text) and ("better direction" in rule_text))
            or ("dead end" in rule_text)
        ):
            found_supported_convention = True
        assert_evidence_list(item["source_evidence"])
    assert found_supported_convention, "Need at least one convention about evidence traceability or describing reusable proof experience"


def test_reuse_advice_targets_future_similar_proofs():
    data = load_output()
    advice_blob = " ".join(data["reuse_advice"]).lower()
    assert "recurrence" in advice_blob or "recursive" in advice_blob, "reuse_advice should address recurrence-style proofs"
    assert "induction" in advice_blob or "closed form" in advice_blob or "tail term" in advice_blob, "reuse_advice should help with future similar proofs"
