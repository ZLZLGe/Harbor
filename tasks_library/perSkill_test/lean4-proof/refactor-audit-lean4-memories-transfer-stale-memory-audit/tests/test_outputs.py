from pathlib import Path

import yaml


OUTPUT_PATH = Path("/app/artifacts/refactor-memory-audit.yaml")
ALLOWED_FILES = {
    "legacy_memory_bank.json",
    "refactor_snapshot.md",
    "build_failures.log",
    "module_index.json",
    "migration_guide.md",
}


def load_output():
    assert OUTPUT_PATH.exists(), f"Missing {OUTPUT_PATH}"
    with OUTPUT_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def index_records(records):
    return {record["record_id"]: record for record in records}


def assert_evidence_shape(record):
    evidence = record.get("evidence")
    assert isinstance(evidence, list) and len(evidence) >= 2, f"{record['record_id']} needs at least two evidence items"
    for item in evidence:
        assert isinstance(item.get("file"), str) and item["file"] in ALLOWED_FILES
        assert isinstance(item.get("locator"), str) and item["locator"]
        assert isinstance(item.get("reason"), str) and item["reason"]


def test_top_level_contract_and_summary_counts():
    data = load_output()
    required = {"audit_id", "audited_inputs", "summary", "records", "refresh_queue"}
    assert required.issubset(data), f"Missing top-level keys: {required - set(data)}"
    assert isinstance(data["audit_id"], str) and data["audit_id"]
    assert isinstance(data["audited_inputs"], list) and len(data["audited_inputs"]) == 5
    expected_inputs = {
        "/app/refactor_audit_inputs/legacy_memory_bank.json",
        "/app/refactor_audit_inputs/refactor_snapshot.md",
        "/app/refactor_audit_inputs/build_failures.log",
        "/app/refactor_audit_inputs/module_index.json",
        "/app/refactor_audit_inputs/migration_guide.md",
    }
    assert set(data["audited_inputs"]) == expected_inputs

    summary = data["summary"]
    for key in ["total_records", "valid_count", "needs_review_count", "deprecated_count", "audit_focus"]:
        assert key in summary, f"summary missing {key}"
    assert summary["total_records"] == 5
    assert summary["valid_count"] == 2
    assert summary["needs_review_count"] == 1
    assert summary["deprecated_count"] == 2
    assert summary["valid_count"] + summary["needs_review_count"] + summary["deprecated_count"] == 5
    assert isinstance(summary["audit_focus"], str) and summary["audit_focus"]


def test_record_set_and_status_distribution():
    data = load_output()
    records = data["records"]
    assert isinstance(records, list) and len(records) == 5
    indexed = index_records(records)
    assert set(indexed) == {
        "mem-pp-closed-tail",
        "mem-fa-unfold-top",
        "mem-pc-traceable-citation",
        "mem-td-pow-pos",
        "mem-pp-modcases-parity",
    }

    statuses = [record["status"] for record in records]
    assert statuses.count("valid") == 2
    assert statuses.count("needs_review") == 1
    assert statuses.count("deprecated") == 2

    for record in records:
        for key in [
            "record_id",
            "record_type",
            "status",
            "old_confidence",
            "new_confidence",
            "decision",
            "suggested_update",
            "evidence",
        ]:
            assert key in record, f"{record.get('record_id', 'unknown')} missing {key}"
        assert record["status"] in {"valid", "needs_review", "deprecated"}
        assert 0 <= record["old_confidence"] <= 1
        assert 0 <= record["new_confidence"] <= 1
        assert isinstance(record["decision"], str) and record["decision"]
        assert isinstance(record["suggested_update"], str) and record["suggested_update"]
        if record["status"] in {"needs_review", "deprecated"}:
            assert record["new_confidence"] < record["old_confidence"]
        assert_evidence_shape(record)


def test_closed_tail_pattern_is_downgraded_but_not_removed():
    data = load_output()
    record = index_records(data["records"])["mem-pp-closed-tail"]
    assert record["status"] == "needs_review"
    text = f"{record['decision']} {record['suggested_update']}".lower()
    assert "simple_induction" in text
    assert "library.tactic.induction" in text or "模块路径" in text
    assert "closed" in text or "闭式" in text


def test_valid_records_keep_failure_and_citation_memories():
    data = load_output()
    indexed = index_records(data["records"])

    failed = indexed["mem-fa-unfold-top"]
    assert failed["status"] == "valid"
    failed_text = f"{failed['decision']} {failed['suggested_update']}".lower()
    assert "closed" in failed_text or "闭式" in failed_text
    assert "unfold" in failed_text or "展开" in failed_text

    citation = indexed["mem-pc-traceable-citation"]
    assert citation["status"] == "valid"
    citation_text = f"{citation['decision']} {citation['suggested_update']}".lower()
    assert "/" in citation_text or "相对路径" in citation_text
    assert "theorem" in citation_text or "line hint" in citation_text or "定理" in citation_text or "行号" in citation_text


def test_deprecated_records_name_required_replacements():
    data = load_output()
    indexed = index_records(data["records"])

    pow_pos = indexed["mem-td-pow-pos"]
    assert pow_pos["status"] == "deprecated"
    pow_text = f"{pow_pos['decision']} {pow_pos['suggested_update']}"
    assert "pow_pos_of_pos" in pow_text
    assert "pow_pos" in pow_text

    parity = indexed["mem-pp-modcases-parity"]
    assert parity["status"] == "deprecated"
    parity_text = f"{parity['decision']} {parity['suggested_update']}"
    assert "mod_cases n % 2" in parity_text
    assert "Int.ModEq" in parity_text


def test_refresh_queue_covers_all_non_valid_records_in_priority_order():
    data = load_output()
    queue = data["refresh_queue"]
    assert isinstance(queue, list) and len(queue) >= 3
    priorities = [item["priority"] for item in queue]
    assert all(isinstance(priority, int) for priority in priorities)
    assert priorities == sorted(priorities), "refresh_queue must be sorted from highest priority to lowest"
    for item in queue:
        for key in ["record_id", "priority", "next_step"]:
            assert key in item, f"refresh_queue entry missing {key}"
        assert isinstance(item["next_step"], str) and item["next_step"]

    queued_ids = {item["record_id"] for item in queue}
    assert {
        "mem-td-pow-pos",
        "mem-pp-modcases-parity",
        "mem-pp-closed-tail",
    }.issubset(queued_ids)
