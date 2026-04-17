#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
from collections import OrderedDict
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "auth_events.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "auth_gate.json"
output_dir.mkdir(parents=True, exist_ok=True)

flows = []
with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        flow_id = (row.get("flow_id") or "").strip()
        session_ttl_min = int((row.get("session_ttl_min") or "0").strip())
        mfa_enabled = (row.get("mfa_enabled") or "").strip().lower()
        cookie_secure = (row.get("cookie_secure") or "").strip().lower()
        cookie_httponly = (row.get("cookie_httponly") or "").strip().lower()
        token_rotation_days = int((row.get("token_rotation_days") or "0").strip())
        failed_logins_24h = int((row.get("failed_logins_24h") or "0").strip())

        risk_score = 0
        reasons = []

        if mfa_enabled == "no":
            risk_score += 40
            reasons.append("mfa_missing")
        if cookie_secure == "no":
            risk_score += 20
            reasons.append("cookie_not_secure")
        if cookie_httponly == "no":
            risk_score += 20
            reasons.append("cookie_not_httponly")
        if token_rotation_days > 30:
            risk_score += 10
            reasons.append("rotation_too_slow")
        if failed_logins_24h >= 10:
            risk_score += 10
            reasons.append("bruteforce_risk")
        if session_ttl_min > 1440:
            risk_score += 10
            reasons.append("session_ttl_too_long")

        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        if mfa_enabled == "no" or cookie_secure == "no" or cookie_httponly == "no" or risk_score >= 60:
            status = "blocked"
        elif risk_score >= 30:
            status = "review"
        else:
            status = "pass"

        flows.append(
            OrderedDict(
                [
                    ("flow_id", flow_id),
                    ("status", status),
                    ("risk_level", risk_level),
                    ("risk_score", risk_score),
                    ("reasons", reasons),
                ]
            )
        )

flows.sort(key=lambda item: item["flow_id"])
blocked_flows = sum(1 for item in flows if item["status"] == "blocked")

payload = OrderedDict(
    [
        (
            "summary",
            OrderedDict(
                [
                    ("total_flows", len(flows)),
                    ("blocked_flows", blocked_flows),
                ]
            ),
        ),
        ("flows", flows),
    ]
)

with output_path.open("w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
