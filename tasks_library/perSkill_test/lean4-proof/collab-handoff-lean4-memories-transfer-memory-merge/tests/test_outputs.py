import json
from pathlib import Path


APP_ROOT = Path("/app")
OUTPUT_PATH = APP_ROOT / "artifacts" / "collab-handoff-memory-pack.json"
INPUT_ROOT = APP_ROOT / "handoff_inputs"


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


def load_source_exports():
    mira = load_json(INPUT_ROOT / "collaborator_mira_export.json")
    noah = load_json(INPUT_ROOT / "collaborator_noah_export.json")
    return mira, noah


def index_by_record_id(items):
    return {item["record_id"]: item for item in items}


def all_output_records(data):
    merged = data["merged_records"]
    items = []
    for key in [
        "proof_patterns",
        "failed_approaches",
        "project_conventions",
        "theorem_dependencies",
    ]:
        items.extend(merged[key])
    return items


def output_record_ids(data):
    return {item["record_id"] for item in all_output_records(data)}


def assert_non_empty_string_list(values, message):
    assert isinstance(values, list) and values, message
    assert all(isinstance(item, str) and item for item in values), message


def assert_source_evidence(items, tracked_files):
    for item in items:
        evidence = item.get("source_evidence")
        assert isinstance(evidence, list) and evidence, f"{item['record_id']} needs non-empty source_evidence"
        for entry in evidence:
            assert isinstance(entry.get("file"), str) and entry["file"], "evidence.file must be a non-empty string"
            assert isinstance(entry.get("line_hint"), str) and entry["line_hint"], "evidence.line_hint must be a non-empty string"
            assert entry["file"] in tracked_files, f"Untracked evidence file: {entry['file']}"


def test_top_level_contract_and_sources():
    data = load_output()
    required = {
        "handoff_id",
        "source_exports",
        "merge_summary",
        "merged_records",
        "conflict_resolutions",
        "dropped_records",
        "handoff_guidance",
    }
    assert required.issubset(data), f"Missing top-level keys: {required - set(data)}"
    assert isinstance(data["handoff_id"], str) and data["handoff_id"]

    expected_sources = {
        "/app/handoff_inputs/collaborator_mira_export.json",
        "/app/handoff_inputs/collaborator_noah_export.json",
        "/app/handoff_inputs/project_file_inventory.json",
        "/app/handoff_inputs/conflict_notes.md",
    }
    assert expected_sources.issubset(set(data["source_exports"])), "source_exports should cover all handoff inputs"
    assert isinstance(data["handoff_guidance"], list) and len(data["handoff_guidance"]) >= 3


def test_merge_summary_counts_and_deduplicated_groups():
    data = load_output()
    mira, noah = load_source_exports()
    summary = data["merge_summary"]
    assert set(summary["input_record_counts"]) == {
        "collaborator_mira_export.json",
        "collaborator_noah_export.json",
    }
    assert summary["input_record_counts"]["collaborator_mira_export.json"] == len(mira["records"])
    assert summary["input_record_counts"]["collaborator_noah_export.json"] == len(noah["records"])

    output_counts = summary["output_record_counts"]
    assert output_counts["proof_patterns"] == len(data["merged_records"]["proof_patterns"]) == 1
    assert output_counts["failed_approaches"] == len(data["merged_records"]["failed_approaches"]) == 2
    assert output_counts["project_conventions"] == len(data["merged_records"]["project_conventions"]) == 1
    assert output_counts["theorem_dependencies"] == len(data["merged_records"]["theorem_dependencies"]) == 1

    groups = summary["deduplicated_groups"]
    assert isinstance(groups, list) and len(groups) >= 3

    record_ids = output_record_ids(data)
    for group in groups:
        assert isinstance(group.get("topic"), str) and group["topic"], "deduplicated group needs a topic"
        assert_non_empty_string_list(group.get("merged_record_ids"), "deduplicated group needs merged_record_ids")
        assert isinstance(group.get("kept_record_id"), str) and group["kept_record_id"], "deduplicated group needs kept_record_id"
        assert isinstance(group.get("reason"), str) and group["reason"], "deduplicated group needs reason"
        assert group["kept_record_id"] in record_ids, "kept_record_id should refer to a surviving record"

    expected_groups = [
        {"mira-pp-recursive-bound-closed-form", "noah-pp-closed-form-tail-control"},
        {"mira-pc-relative-evidence", "noah-pc-evidence-path-and-line"},
        {"mira-td-positivity", "noah-td-pow-pos"},
    ]
    actual_groups = [set(group["merged_record_ids"]) for group in groups]
    for expected_group in expected_groups:
        assert any(
            expected_group.issubset(actual_group)
            for actual_group in actual_groups
        ), "deduplicated_groups should describe the documented merge/conflict sets"


def test_merged_proof_pattern_is_deduplicated_and_prefers_stronger_evidence():
    data = load_output()
    inventory = load_json(INPUT_ROOT / "project_file_inventory.json")
    tracked_files = set(inventory["tracked_files"])

    patterns = data["merged_records"]["proof_patterns"]
    assert len(patterns) == 1, "Near-duplicate proof patterns should be merged into a single canonical record"
    pattern = patterns[0]
    for key in [
        "record_id",
        "record_type",
        "canonical_title",
        "merged_from",
        "decision_reason",
        "source_evidence",
        "goal_signals",
        "recommended_steps",
        "helper_lemmas",
    ]:
        assert key in pattern, f"Proof pattern missing {key}"
    assert set(pattern["merged_from"]) == {
        "mira-pp-recursive-bound-closed-form",
        "noah-pp-closed-form-tail-control",
    }
    assert isinstance(pattern["goal_signals"], list)
    assert isinstance(pattern["recommended_steps"], list) and len(pattern["recommended_steps"]) >= 2
    assert isinstance(pattern["helper_lemmas"], list)
    assert_source_evidence(patterns, tracked_files)


def test_failed_approaches_both_survive_as_distinct_dead_ends():
    data = load_output()
    failed = data["merged_records"]["failed_approaches"]
    assert len(failed) == 2, "Both failed approaches should remain after the merge"
    covered_sources = set()
    for item in failed:
        for key in [
            "record_id",
            "record_type",
            "canonical_title",
            "merged_from",
            "decision_reason",
            "source_evidence",
            "attempted_step",
            "failure_signal",
            "better_direction",
        ]:
            assert key in item, f"Failed approach missing {key}"
        covered_sources.update(item["merged_from"])
    assert covered_sources == {
        "mira-fa-simp-recursion-too-early",
        "noah-fa-linarith-before-unfolding",
    }


def test_single_citation_convention_and_single_explicit_dependency():
    data = load_output()
    inventory = load_json(INPUT_ROOT / "project_file_inventory.json")
    tracked_files = set(inventory["tracked_files"])

    conventions = data["merged_records"]["project_conventions"]
    assert len(conventions) == 1, "Only one canonical citation convention should remain"
    convention = conventions[0]
    assert set(convention["merged_from"]) == {
        "mira-pc-relative-evidence",
        "noah-pc-evidence-path-and-line",
    }
    text = f"{convention['canonical_title']} {convention['rule']} {convention['reason']}".lower()
    assert ("repository-relative" in text) or ("仓库相对路径" in text)
    assert ("line hint" in text) or ("theorem name" in text) or ("theorem 名" in text)
    assert_source_evidence(conventions, tracked_files)

    deps = data["merged_records"]["theorem_dependencies"]
    assert len(deps) == 1, "Only one canonical dependency should remain for positive-tail bounds"
    dep = deps[0]
    assert set(dep["merged_from"]) == {
        "mira-td-positivity",
        "noah-td-pow-pos",
    }
    assert dep["theorem"] == "pow_pos", "The explicit theorem dependency should win"
    assert dep["preferred_source"] in tracked_files
    assert_source_evidence(deps, tracked_files)


def test_conflict_resolutions_and_dropped_records_are_explicit():
    data = load_output()
    record_ids = output_record_ids(data)
    resolutions = data["conflict_resolutions"]
    assert isinstance(resolutions, list) and len(resolutions) >= 3
    conflict_sets = []
    for item in resolutions:
        assert isinstance(item.get("topic"), str) and item["topic"], "conflict resolution needs a topic"
        assert isinstance(item.get("winner_record_id"), str) and item["winner_record_id"], "conflict resolution needs winner_record_id"
        assert_non_empty_string_list(item.get("loser_record_ids"), "conflict resolution needs loser_record_ids")
        assert isinstance(item.get("resolution_reason"), str) and item["resolution_reason"], "conflict resolution needs resolution_reason"
        assert item["winner_record_id"] in record_ids, "winner_record_id should refer to a surviving record"
        conflict_sets.append(frozenset(item["loser_record_ids"]))

    assert any(
        {"mira-pp-recursive-bound-closed-form", "noah-pp-closed-form-tail-control"}.issubset(conflict_set)
        for conflict_set in conflict_sets
    ), "conflict_resolutions should explain the proof-pattern merge"
    assert any(
        {"mira-pc-relative-evidence", "noah-pc-evidence-path-and-line"}.issubset(conflict_set)
        for conflict_set in conflict_sets
    ), "conflict_resolutions should explain the citation-convention merge"
    assert any(
        "mira-td-positivity" in conflict_set
        for conflict_set in conflict_sets
    ), "conflict_resolutions should explain why the automation-style dependency lost"

    dropped = data["dropped_records"]
    assert isinstance(dropped, list) and len(dropped) >= 2
    dropped_ids = set()
    for item in dropped:
        assert isinstance(item.get("record_id"), str) and item["record_id"], "dropped record needs record_id"
        assert isinstance(item.get("drop_reason"), str) and item["drop_reason"], "dropped record needs drop_reason"
        assert isinstance(item.get("replaced_by"), str) and item["replaced_by"], "dropped record needs replaced_by"
        assert item["replaced_by"] in record_ids, "replaced_by should refer to a surviving record"
        dropped_ids.add(item["record_id"])

    assert dropped_ids & {
        "mira-pc-relative-evidence",
        "noah-pc-evidence-path-and-line",
    }, "At least one superseded citation rule should be listed in dropped_records"
    assert "mira-td-positivity" in dropped_ids, "The automation-style dependency should appear in dropped_records"


def test_handoff_guidance_targets_the_next_collaborator():
    data = load_output()
    guidance = data["handoff_guidance"]
    assert isinstance(guidance, list) and len(guidance) >= 3
    assert all(isinstance(item, str) and item.strip() for item in guidance), "handoff_guidance should contain non-empty strings"
