from __future__ import annotations

from conftest import OUT_DIR, broker_audit, load_json, reset_and_run


EXPECTED_RELEASE_ID = "2026.04.18-rc1"
EXPECTED_PLAN_ID = "promo-20260418-01"


def test_release_bundle_matches_live_broker_contract() -> None:
    result = reset_and_run()
    assert result.returncode == 0, result.stderr or result.stdout

    bundle = load_json(OUT_DIR / "release-bundle.json")
    assert bundle["release_id"] == EXPECTED_RELEASE_ID
    assert bundle["source"] == "broker"
    assert bundle["summary"] == {
        "artifact_count": 4,
        "deployable_count": 3,
        "attested_count": 3,
        "promotion_ready_count": 3,
    }

    artifacts = {item["artifact_id"]: item for item in bundle["artifacts"]}
    assert set(artifacts) == {
        "gh-linux-amd64",
        "gh-linux-arm64",
        "helm-linux-amd64",
        "helm-checksums",
    }
    assert artifacts["gh-linux-amd64"]["provenance_verified"] is True
    assert artifacts["gh-linux-arm64"]["provenance_verified"] is True
    assert artifacts["helm-linux-amd64"]["provenance_verified"] is True
    assert artifacts["helm-checksums"]["deployable"] is False
    assert artifacts["helm-checksums"]["provenance_verified"] is False


def test_promotion_plan_matches_live_broker_plan() -> None:
    result = reset_and_run()
    assert result.returncode == 0, result.stderr or result.stdout

    plan = load_json(OUT_DIR / "promotion-plan.json")
    assert plan["release_id"] == EXPECTED_RELEASE_ID
    assert plan["source"] == "broker"
    assert plan["plan_id"] == EXPECTED_PLAN_ID

    promotions = plan["promotions"]
    assert [item["artifact_id"] for item in promotions] == [
        "gh-linux-amd64",
        "gh-linux-arm64",
        "helm-linux-amd64",
    ]
    assert [item["target_environment"] for item in promotions] == [
        "staging",
        "staging",
        "staging",
    ]


def test_release_summary_records_live_sources() -> None:
    result = reset_and_run()
    assert result.returncode == 0, result.stderr or result.stdout

    summary = (OUT_DIR / "release-summary.md").read_text(encoding="utf-8")
    assert "bundle_source: broker" in summary
    assert "promotion_source: broker" in summary
    assert f"plan_id: {EXPECTED_PLAN_ID}" in summary
    assert "fallback_snapshot" not in summary


def test_real_broker_endpoints_are_used() -> None:
    result = reset_and_run()
    assert result.returncode == 0, result.stderr or result.stdout

    audit = broker_audit()
    authorized_paths = [event["path"] for event in audit["events"] if event["authorized"]]
    assert "/api/v1/release-candidates" in authorized_paths, audit
    assert "/api/v1/provenance" in authorized_paths, audit
    assert "/api/v1/promotion-plan" in authorized_paths, audit
