from __future__ import annotations

from conftest import (
    DECK_HTML_PATH,
    RECEIPT_PATH,
    SUBMISSION_PATH,
    WORKSPACE_ROOT,
    collect_external_urls,
    html_text,
    load_json,
)


def test_hidden_service_and_protected_inputs_unchanged() -> None:
    protected_inputs = [
        WORKSPACE_ROOT / "brief" / "creative_brief.md",
        WORKSPACE_ROOT / "specs" / "deck_contract.md",
        WORKSPACE_ROOT / "data" / "weekly_kpis.csv",
        WORKSPACE_ROOT / "data" / "feature_matrix.csv",
        WORKSPACE_ROOT / "data" / "customer_quotes.json",
        WORKSPACE_ROOT / "data" / "user_journey.json",
    ]
    for path in protected_inputs:
        assert path.exists(), f"Missing protected input: {path}"


def test_deck_has_no_external_runtime_dependencies() -> None:
    html = html_text()
    external_urls = collect_external_urls(html)
    assert not external_urls, f"Deck must render offline; found external URLs: {external_urls}"


def test_submission_and_receipt_are_not_placeholder_payloads() -> None:
    submission = load_json(SUBMISSION_PATH)
    receipt = load_json(RECEIPT_PATH)

    assert submission["job_id"]
    assert receipt["job_id"] == submission["job_id"]
    assert receipt["rendered_slide_count"] == submission["slide_count"] == 6


def test_required_outputs_exist_in_expected_locations() -> None:
    assert DECK_HTML_PATH.exists()
    assert SUBMISSION_PATH.exists()
    assert RECEIPT_PATH.exists()


def test_solver_visible_workspace_does_not_include_hidden_golden_decks() -> None:
    forbidden = [
        WORKSPACE_ROOT / "golden_deck.html",
        WORKSPACE_ROOT / "expected_receipt.json",
        WORKSPACE_ROOT / "reference_submission.json",
        WORKSPACE_ROOT / "layout_answer_key.json",
        WORKSPACE_ROOT / "diagram_answer_key.json",
    ]
    for path in forbidden:
        assert not path.exists(), f"Unexpected solver-visible golden artifact present: {path}"
