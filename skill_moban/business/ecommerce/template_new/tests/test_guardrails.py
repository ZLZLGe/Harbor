from __future__ import annotations

from common import OUT_ROOT, compute_data_hashes, read_collection_soup, reference_hashes, run_build


def test_input_data_hashes_stay_unchanged() -> None:
    expected = reference_hashes()
    actual = compute_data_hashes()
    if expected != actual:
        raise AssertionError(f"input data hash mismatch: expected={expected} actual={actual}")


def test_outputs_rebuild_after_cleanup() -> None:
    for name in ("collection.html", "predictive-search.html", "theme_preview_report.json"):
        path = OUT_ROOT / name
        if path.exists():
            path.unlink()
    run_build()
    for name in ("collection.html", "predictive-search.html", "theme_preview_report.json"):
        if not (OUT_ROOT / name).exists():
            raise AssertionError(f"missing regenerated output: {name}")
    if not read_collection_soup().select(".product-card"):
        raise AssertionError("rebuilt collection output does not contain product cards")
