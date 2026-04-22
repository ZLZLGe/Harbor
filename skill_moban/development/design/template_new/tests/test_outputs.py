from __future__ import annotations

from conftest import (
    DECK_HTML_PATH,
    LAST_VALIDATE_PATH,
    QA_TRACE_PATH,
    RECEIPT_PATH,
    SUBMISSION_PATH,
    canonical_json_sha,
    ensure_service,
    failure_count,
    html_text,
    load_json,
    load_trace_events,
    assert_slide_payload,
)


def test_a_output_files_and_json_shapes_exist() -> None:
    ensure_service()
    assert DECK_HTML_PATH.exists(), "Missing /app/output/deck/index.html"
    assert SUBMISSION_PATH.exists(), "Missing /app/output/deck_submission.json"
    assert RECEIPT_PATH.exists(), "Missing /app/output/deck_receipt.json"

    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)

    assert set(submission.keys()) >= {"job_id", "entry_html", "slide_count", "slides"}
    assert set(receipt.keys()) >= {"accepted", "job_id", "rendered_slide_count"}

    assert submission["entry_html"] == "/app/output/deck/index.html"
    assert submission["slide_count"] == 6
    assert receipt["rendered_slide_count"] == 6


def test_b_submission_roles_and_source_refs_cover_contract() -> None:
    submission = load_json(SUBMISSION_PATH)
    slides = submission["slides"]
    assert isinstance(slides, list) and len(slides) == 6

    seen_roles: set[str] = set()
    for expected_index, slide in enumerate(slides):
        assert_slide_payload(slide, expected_index)
        role = slide.get("role")
        if isinstance(role, str) and role:
            seen_roles.add(role)

    assert len(seen_roles) == 6, "Each slide should describe a distinct page purpose"


def test_c_receipt_reports_clean_live_acceptance() -> None:
    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)

    assert receipt["accepted"] is True
    assert receipt["job_id"] == submission["job_id"]

    failure_fields = sorted(key for key in receipt if key.endswith("_failures"))
    assert failure_fields, "Receipt should report QA failure categories"

    for field in failure_fields:
        assert failure_count(receipt[field]) == 0, f"Receipt reported failures in {field}: {receipt[field]!r}"

    submission_sha = canonical_json_sha(submission)
    trace_events = load_trace_events(QA_TRACE_PATH)
    assert trace_events, "Missing QA trace events; submission must go through the live localhost validator"
    assert any(event.get("event") == "manifest" for event in trace_events), "Solver never fetched live manifest"
    assert any(
        event.get("event") == "validate" and event.get("payload_sha256") == submission_sha
        for event in trace_events
    ), "Solver never posted the final submission payload through the live validator"

    if LAST_VALIDATE_PATH.exists():
        last_validate = load_json(LAST_VALIDATE_PATH)
        assert last_validate["payload_sha256"] == submission_sha
        assert last_validate["accepted"] is True
        assert last_validate["job_id"] == submission["job_id"]


def test_d_final_deck_is_nonempty_html() -> None:
    html = html_text()
    lowered = html.lower()
    assert "<html" in lowered, "Deck output is not HTML"
    assert len(html.strip()) > 1000, "Deck HTML is suspiciously small"
