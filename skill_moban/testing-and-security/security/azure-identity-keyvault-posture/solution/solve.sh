#!/bin/bash
set -e

python3 - <<'PY'
import csv
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "azure_access.csv"
output_dir = workspace_root / "output"
output_path = output_dir / "azure_identity_posture.csv"
output_dir.mkdir(parents=True, exist_ok=True)

ready_ops = {"keys", "secrets", "certificates", "multi"}
preferred_credentials = {"DefaultAzureCredential", "ManagedIdentityCredential"}
rows = []

with input_path.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        app = (row.get("app") or "").strip()
        credential_type = (row.get("credential_type") or "").strip()
        uses_managed_identity = (row.get("uses_managed_identity") or "").strip().lower()
        keyvault_ops = (row.get("keyvault_ops") or "").strip().lower()
        content_safety_enabled = (row.get("content_safety_enabled") or "").strip().lower()
        token_refresh_minutes = int((row.get("token_refresh_minutes") or "0").strip())

        if uses_managed_identity == "yes" and credential_type in preferred_credentials:
            identity_grade = "A"
        elif uses_managed_identity == "yes":
            identity_grade = "B"
        else:
            identity_grade = "C"

        keyvault_readiness = "ready" if keyvault_ops in ready_ops else "missing"
        rotation_needed = "yes" if token_refresh_minutes > 60 or "ClientSecret" in credential_type else "no"

        notes = ";".join(
            [
                "managed_identity" if uses_managed_identity == "yes" else "explicit_credential",
                "kv_ready" if keyvault_readiness == "ready" else "kv_missing",
                "content_safety_on" if content_safety_enabled == "yes" else "content_safety_off",
            ]
        )

        rows.append(
            {
                "app": app,
                "identity_grade": identity_grade,
                "keyvault_readiness": keyvault_readiness,
                "rotation_needed": rotation_needed,
                "notes": notes,
            }
        )

rows.sort(key=lambda row: row["app"])

with output_path.open("w", encoding="utf-8", newline="") as f:
    fieldnames = ["app", "identity_grade", "keyvault_readiness", "rotation_needed", "notes"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
PY
