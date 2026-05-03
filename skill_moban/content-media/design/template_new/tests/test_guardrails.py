from __future__ import annotations

from pathlib import Path

from test_helpers import ANSWER_DIR, DATA_ROOT, REGISTRY_LOG, ensure_built, load_json, sha256


WORLD_HASH = sha256(DATA_ROOT / "series/global_renewables_2014_2023.csv")
COUNTRY_HASH = sha256(DATA_ROOT / "series/country_mix_2023.csv")
SOURCE_HASH = sha256(DATA_ROOT / "sources/source_catalog.json")
SERVICE_HASH = sha256(Path("/services/source-registry/server.py"))


def test_guardrail_01_inputs_unchanged() -> None:
    ensure_built()
    assert WORLD_HASH == sha256(DATA_ROOT / "series/global_renewables_2014_2023.csv"), "world series input was modified"
    assert COUNTRY_HASH == sha256(DATA_ROOT / "series/country_mix_2023.csv"), "country mix input was modified"
    assert SOURCE_HASH == sha256(DATA_ROOT / "sources/source_catalog.json"), "source catalog input was modified"
    assert SERVICE_HASH == sha256(Path("/services/source-registry/server.py")), "source registry service was modified"


def test_guardrail_02_not_a_long_scrolling_page() -> None:
    ensure_built()
    html = (ANSWER_DIR / "presentation.html").read_text(encoding="utf-8")
    lowered = html.lower()
    assert "height: 100vh" in lowered or "height:100vh" in lowered, "deck is missing viewport-sized slide styling"
    assert "touchstart" in lowered and "wheel" in lowered and "keydown" in lowered, (
        "deck is missing one or more required navigation input handlers"
    )


def test_guardrail_03_audit_consistency() -> None:
    ensure_built()
    manifest = load_json(ANSWER_DIR / "presentation_manifest.json")
    audit = load_json(ANSWER_DIR / "source_audit.json")
    manifest_sources = set(manifest["source_ids_used"])
    audit_sources = {entry["source_id"] for entry in audit["sources_resolved"]}
    assert manifest_sources == audit_sources, "manifest and source_audit disagree on which sources were used"
    assert REGISTRY_LOG.exists(), "registry log disappeared before guardrail checks"
