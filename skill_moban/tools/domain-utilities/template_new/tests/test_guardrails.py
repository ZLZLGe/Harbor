from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from conftest import load_output_json


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_protected_inputs_and_skill_files_are_unchanged() -> None:
    manifest_path = Path(os.environ.get("PROTECTED_HASHES_PATH", "/opt/domain-task/protected_hashes.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for path_str, expected_hash in manifest.items():
        path = Path(path_str)
        assert path.exists(), path
        assert _sha256(path) == expected_hash, path


def test_b_no_placeholder_or_partial_rank_output() -> None:
    payload = load_output_json()
    assert len(payload["buy_now_ranked"]) == 3
    assert payload["top_pick"] == payload["buy_now_ranked"][0]
    statuses = {row["status"] for row in payload["evaluations"]}
    assert statuses == {"buy_now", "monitor", "reject"}


def test_c_rejected_domains_stay_rejected_for_real_policy_reasons() -> None:
    payload = load_output_json()
    index = {row["domain"]: row for row in payload["evaluations"]}
    assert index["calltitanhq.com"]["status"] == "reject"
    assert "TRADEMARK_COLLISION" in index["calltitanhq.com"]["reason_codes"]
    assert index["fieldopsgrid.com"]["status"] == "reject"
    assert "ARCHIVE_MISMATCH" in index["fieldopsgrid.com"]["reason_codes"]
