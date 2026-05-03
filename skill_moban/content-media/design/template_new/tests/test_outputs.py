from __future__ import annotations

from test_helpers import (
    ANSWER_DIR,
    DATA_ROOT,
    PREVIEW_ROOT,
    PREVIEW_ROOT_ALT,
    REGISTRY_LOG,
    browser_snapshot,
    ensure_built,
    load_json,
    navigation_probe,
)


REQUIRED_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 720},
    {"width": 768, "height": 1024},
    {"width": 375, "height": 667},
    {"width": 667, "height": 375},
]

def test_01_required_outputs_and_contracts() -> None:
    ensure_built()
    html_path = ANSWER_DIR / "presentation.html"
    manifest_path = ANSWER_DIR / "presentation_manifest.json"
    audit_path = ANSWER_DIR / "source_audit.json"
    assert html_path.exists(), "presentation.html was not created"
    assert manifest_path.exists(), "presentation_manifest.json was not created"
    assert audit_path.exists(), "source_audit.json was not created"

    manifest = load_json(manifest_path)
    audit = load_json(audit_path)
    assert manifest["slide_count"] == 8, f"expected 8 slides, found {manifest['slide_count']}"
    assert len(manifest["slides"]) == 8, "manifest slides array must contain 8 entries"
    assert set(manifest["viewport_targets"]) == {
        "1920x1080",
        "1280x720",
        "768x1024",
        "375x667",
        "667x375",
    }, "manifest viewport_targets must cover the required 5 sizes"
    assert audit["registry_checked"] is True, "source_audit.json must record a real registry check"
    assert audit["registry_endpoint"] == "http://127.0.0.1:4873", "registry endpoint must point at the local service"


def test_02_registry_was_actually_used() -> None:
    ensure_built()
    assert REGISTRY_LOG.exists(), "source registry request log was not created"
    lines = [line.strip() for line in REGISTRY_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert "/health" in lines, "build did not hit the registry health endpoint"
    for source_id in [
        "owid-energy-data",
        "iea-tripling-2030",
        "iea-pledge-update-2025",
        "irena-capacity-stats-2025",
    ]:
        assert f"/sources/{source_id}" in lines, f"build did not resolve source id {source_id} via the registry"


def test_03_browser_structure_and_dom_text() -> None:
    ensure_built()
    snap = browser_snapshot({"width": 1280, "height": 720})
    assert snap["slideCount"] == 8, f"browser rendered {snap['slideCount']} slides instead of 8"
    assert snap["activeSlideId"], "no active slide could be detected"
    assert snap["progressText"], "deck is missing a visible slide progress indicator"
    assert snap["hasCanvas"] == 0, "deck should not depend on canvas-rendered slide content"
    assert not snap["hasFullBleedImageOnly"], "slides cannot be rasterized into image-only panels"
    assert all(item["textLength"] > 40 for item in snap["overflow"]), "every slide must keep real DOM text, not placeholder fragments"


def test_04_offline_integrity_and_sources_in_dom() -> None:
    ensure_built()
    snap = browser_snapshot({"width": 1280, "height": 720})
    assert not snap["remoteRefs"], f"deck must not contain remote asset references: {snap['remoteRefs']}"
    assert all(url.startswith(("http://127.0.0.1:8765/", "data:", "blob:")) for url in snap["requests"]), (
        f"deck made disallowed browser requests: {snap['requests']}"
    )
    source_ids = {node["sourceId"] for node in snap["sourceNodes"]}
    required = {
        "owid-energy-data",
        "iea-tripling-2030",
        "iea-pledge-update-2025",
        "irena-capacity-stats-2025",
    }
    assert required.issubset(source_ids), f"missing required source chips in DOM: {sorted(required - source_ids)}"


def test_05_navigation_keyboard_wheel_touch() -> None:
    ensure_built()
    probe = navigation_probe()
    assert probe["initial"]["id"] != probe["after_key"]["id"], "ArrowRight must move to a different slide"
    assert probe["after_key"]["id"] != probe["after_wheel"]["id"], "wheel navigation must move to a different slide"
    assert probe["after_wheel"]["id"] != probe["after_touch"]["id"], "touch swipe navigation must move to a different slide"
    for label in ["initial", "after_key", "after_wheel", "after_touch"]:
        assert probe[label]["scrollY"] <= 2, f"{label} changed by document scrolling instead of deck-state navigation"
    assert probe["after_touch"]["progress"], "progress indicator did not remain visible after navigation"


def test_06_viewport_fit_no_internal_scrolling() -> None:
    ensure_built()
    for viewport in REQUIRED_VIEWPORTS:
        snap = browser_snapshot(viewport)
        for slide in snap["overflow"]:
            assert slide["rectTop"] >= -2, f"{viewport}: slide {slide['id']} starts outside the viewport"
            assert slide["rectBottom"] <= viewport["height"] + 2, f"{viewport}: slide {slide['id']} extends beyond the viewport"
            assert slide["scrollHeight"] <= slide["clientHeight"] + 2, (
                f"{viewport}: slide {slide['id']} has internal scrolling content"
            )
            assert slide["footerBottom"] <= viewport["height"] + 2, (
                f"{viewport}: slide {slide['id']} footer is clipped below the viewport"
            )


def test_07_reduced_motion_still_usable() -> None:
    ensure_built()
    snap = browser_snapshot({"width": 1280, "height": 720}, reduced_motion="reduce")
    assert snap["slideCount"] == 8, "reduced-motion mode changed the rendered slide count"
    assert snap["activeSlideId"], "reduced-motion mode left the deck without an active slide"
    assert not snap["console"], f"reduced-motion mode triggered browser console errors: {snap['console']}"


def test_08_manifest_and_chart_mapping() -> None:
    ensure_built()
    manifest = load_json(ANSWER_DIR / "presentation_manifest.json")
    html = (ANSWER_DIR / "presentation.html").read_text(encoding="utf-8")
    for chart_id in ["global_growth_line", "mix_shift_stack", "country_compare_bars"]:
        assert chart_id in html, f"required chart id {chart_id} is missing from presentation.html"
    slide_ids = {slide["slide_id"] for slide in manifest["slides"]}
    for slide_id in [
        "slide-cover",
        "slide-summary",
        "slide-growth",
        "slide-mix",
        "slide-country",
        "slide-risks",
        "slide-actions",
        "slide-sources",
    ]:
        assert slide_id in slide_ids, f"manifest is missing required slide id {slide_id}"


def test_09_style_exploration_and_preset_traceability() -> None:
    ensure_built()
    preview_files = sorted(PREVIEW_ROOT.glob("*.html"))
    preview_root = PREVIEW_ROOT
    if not preview_files:
        preview_files = sorted(PREVIEW_ROOT_ALT.glob("*.html"))
        preview_root = PREVIEW_ROOT_ALT
    assert len(preview_files) == 3, f"expected 3 preview files in {preview_root}, found {len(preview_files)}"

    for preview in preview_files:
        text = preview.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in text, f"{preview.name} must be a self-contained HTML preview"
        assert "<section" in text or "<main" in text, f"{preview.name} must render an actual slide preview"
