from __future__ import annotations

from pathlib import Path

import yaml

from conftest import OUT_DIR, broker_integrity, load_json, reset_and_run


EXPECTED_SERVER_SHA256 = "ca75016cec9e1da6bae298cb2e1bb62df3288105c7b94234dc91c827080853ca"
EXPECTED_DATA_SHA256 = "3c01e12412539a1874b87fa52167f5679f5cc4b32ca766f437b33541b9d7bb1a"
WORKFLOW_PATH = Path("/app/workspace/.github/workflows/release-dry-run.yml")


def test_hidden_broker_and_frozen_data_unchanged() -> None:
    integrity = broker_integrity()
    assert integrity["server_sha256"] == EXPECTED_SERVER_SHA256
    assert integrity["data_sha256"] == EXPECTED_DATA_SHA256


def test_workflow_shape_is_preserved() -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert list(jobs) == ["inspect", "package", "promote", "attest"] or list(jobs) == [
        "inspect",
        "package",
        "attest",
        "promote",
    ]
    assert jobs["package"]["needs"] == ["inspect"]
    assert jobs["attest"]["needs"] == ["package"]
    assert jobs["promote"]["needs"] == ["attest"]
    assert jobs["inspect"]["run"].startswith("python /app/workspace/scripts/")
    assert jobs["package"]["run"].startswith("python /app/workspace/scripts/")
    assert jobs["attest"]["run"].startswith("python /app/workspace/scripts/")
    assert jobs["promote"]["run"].startswith("python /app/workspace/scripts/")


def test_outputs_do_not_fall_back_to_historical_snapshots() -> None:
    result = reset_and_run()
    assert result.returncode == 0, result.stderr or result.stdout

    bundle = load_json(OUT_DIR / "release-bundle.json")
    plan = load_json(OUT_DIR / "promotion-plan.json")
    assert bundle["source"] == "broker"
    assert plan["source"] == "broker"
