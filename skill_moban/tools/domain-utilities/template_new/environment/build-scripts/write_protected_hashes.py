#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protected = [
        Path("/app/data/candidate_domains.csv"),
        Path("/app/data/authority_metrics.csv"),
        Path("/app/data/sales_comps.csv"),
        Path("/app/data/trademark_flags.csv"),
        Path("/app/data/scoring_policy.md"),
        Path("/services/domain-audit/server.py"),
        Path("/services/domain-audit/audit_impl.py"),
        Path("/app/.codex/skills/domain-acquisition-research/SKILL.md"),
        Path("/app/.codex/skills/domain-acquisition-research/scripts/probe_manifest.py"),
        Path("/app/.codex/skills/domain-acquisition-research/scripts/pull_domain_snapshot.py"),
        Path("/app/.codex/skills/domain-acquisition-research/scripts/recompute_domain_scores.py"),
        Path("/app/.codex/skills/domain-acquisition-research/scripts/validate_report_contract.py"),
        Path("/app/.codex/skills/domain-acquisition-research/scripts/package_report_stub.py"),
    ]
    payload: dict[str, str] = {}
    for path in protected:
        if path.exists():
            payload[str(path)] = sha256(path)
    for path in sorted(Path("/app/data/archive_summaries").glob("*.md")):
        payload[str(path)] = sha256(path)
    for path in sorted(Path("/services/domain-audit/snapshots").glob("*.json")):
        payload[str(path)] = sha256(path)
    Path("/opt/domain-task/protected_hashes.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
