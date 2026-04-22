from __future__ import annotations

from conftest import RECEIPT_PATH, SUBMISSION_PATH, collect_external_urls, html_text, load_json


def test_submission_slide_manifest_matches_rendered_contract() -> None:
    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)

    assert submission["slide_count"] == 6
    assert len(submission["slides"]) == 6
    assert receipt["rendered_slide_count"] == 6


def test_receipt_confirms_navigation_and_visual_contracts() -> None:
    receipt = load_json(RECEIPT_PATH)

    assert receipt["accepted"] is True
    assert not collect_external_urls(html_text()), "Deck must remain offline-safe at runtime"

    failure_fields = [key for key in receipt if key.endswith("_failures")]
    assert failure_fields, "Receipt is missing QA failure categories"
    for field in failure_fields:
        assert receipt[field] in (0, []), f"Receipt reported failures in {field}: {receipt[field]!r}"
