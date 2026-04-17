#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import re
from collections import OrderedDict
from pathlib import Path


AREA_RULES = [
    {
        "aliases": ["node operation"],
        "test_layer": "unit",
        "test_pattern": "NodeTestHarness + nock",
        "key_location": "packages/nodes-base/nodes/*/test/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "node-operation-regression",
    },
    {
        "aliases": ["node credential"],
        "test_layer": "unit",
        "test_pattern": "jest-mock-extended",
        "key_location": "packages/nodes-base/nodes/*/test/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "node-credential-regression",
    },
    {
        "aliases": ["trigger webhook"],
        "test_layer": "unit",
        "test_pattern": "mock IHookFunctions + jest.mock GenericFunctions",
        "key_location": "packages/nodes-base/nodes/*/test/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "trigger-webhook-regression",
    },
    {
        "aliases": ["binary data"],
        "test_layer": "unit",
        "test_pattern": "NodeTestHarness assertBinaryData",
        "key_location": "packages/core/nodes-testing/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "binary-data-regression",
    },
    {
        "aliases": ["execution engine"],
        "test_layer": "integration",
        "test_pattern": "WorkflowRunner + DI container",
        "key_location": "packages/cli/src/__tests__/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "execution-engine-regression",
    },
    {
        "aliases": ["cli / api", "cli/api", "api", "cli"],
        "test_layer": "API",
        "test_pattern": "setupTestServer + supertest",
        "key_location": "packages/cli/test/integration/",
        "artifact_mode": "bug-check-suite",
        "artifact_suffix": "api-contract-suite",
    },
    {
        "aliases": ["config"],
        "test_layer": "unit",
        "test_pattern": "GlobalConfig + Container",
        "key_location": "packages/@n8n/config/src/__tests__/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "config-regression",
    },
    {
        "aliases": ["editor ui"],
        "test_layer": "UI",
        "test_pattern": "Vue Test Utils + Pinia",
        "key_location": "packages/frontend/editor-ui/src/**/__tests__/",
        "artifact_mode": "failing-test",
        "artifact_suffix": "editor-ui-regression",
    },
    {
        "aliases": ["e2e / canvas", "e2e/canvas", "canvas"],
        "test_layer": "E2E",
        "test_pattern": "Test containers + composables",
        "key_location": "packages/testing/playwright/",
        "artifact_mode": "bug-check-suite",
        "artifact_suffix": "playwright-path-suite",
    },
]


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "ticket"


def route_area(area: str) -> dict:
    normalized = normalize_text(area)
    for rule in AREA_RULES:
        for alias in rule["aliases"]:
            if alias in normalized:
                return rule
    raise ValueError(f"Unsupported area: {area}")


def build_artifact(ticket_id: str, rule: dict, parity_check: str) -> str:
    ticket_slug = slugify(ticket_id)
    if rule["artifact_mode"] == "bug-check-suite" and parity_check == "sandbox+production":
        return f"bug-check-suite::{ticket_slug}::sandbox-production-contract"
    return f"{rule['artifact_mode']}::{ticket_slug}::{rule['artifact_suffix']}"


def build_fix_hint(ticket: dict, rule: dict) -> str:
    key_location = rule["key_location"]
    external_api = str(ticket.get("external_api") or "").strip()
    ui_surface = str(ticket.get("ui_surface") or "").strip()
    if ticket.get("has_sandbox_mode") and ticket.get("has_production_mode"):
        return f"align sandbox and production assertions in {key_location}"
    if ticket.get("has_workflow_json") and ticket.get("has_stacktrace"):
        return f"replay the workflow fixture and patch the stacktrace path in {key_location}"
    if external_api.lower() not in {"", "none"}:
        return f"stub {external_api} with deterministic fixtures before fixing {key_location}"
    if ui_surface.lower() not in {"", "none"}:
        return f"lock the {ui_surface} interaction contract in {key_location}"
    if ticket.get("has_workflow_json"):
        return f"replay the workflow fixture and preserve the corrected behavior in {key_location}"
    if ticket.get("has_stacktrace"):
        return f"patch the stacktrace branch and keep the regression in {key_location}"
    return f"encode the reported failure as a focused regression in {key_location}"


workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
input_path = workspace_root / "input" / "bug_tickets.json"
output_dir = workspace_root / "output"
output_path = output_dir / "regression_harness.json"
output_dir.mkdir(parents=True, exist_ok=True)

with input_path.open("r", encoding="utf-8") as f:
    tickets = json.load(f)

decisions = []
for ticket in tickets:
    ticket_id = str(ticket["ticket_id"]).strip()
    rule = route_area(str(ticket["area"]))
    parity_check = (
        "sandbox+production"
        if ticket.get("has_sandbox_mode") and ticket.get("has_production_mode")
        else "single-path"
    )
    decisions.append(
        OrderedDict(
            [
                ("ticket_id", ticket_id),
                ("test_layer", rule["test_layer"]),
                ("test_pattern", rule["test_pattern"]),
                ("key_location", rule["key_location"]),
                ("parity_check", parity_check),
                ("artifact", build_artifact(ticket_id, rule, parity_check)),
                ("fix_hint", build_fix_hint(ticket, rule)),
            ]
        )
    )

decisions.sort(key=lambda item: item["ticket_id"])

with output_path.open("w", encoding="utf-8") as f:
    json.dump(decisions, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
