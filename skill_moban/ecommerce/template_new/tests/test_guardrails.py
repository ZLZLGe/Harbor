from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path("/var/log/ecommerce-recon/access.log")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("client", "").startswith("verifier-"):
            continue
        records.append(record)
    return records


def test_solver_used_live_service_chain_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    graphql = [r for r in records if r["method"] == "POST" and r["path"] == "/admin/graphql"]
    assert any('"orders"' in r.get("body", "") or "orders" in r.get("body", "") for r in graphql), "Solver did not query live orders"
    assert any('"productVariants"' in r.get("body", "") or "productVariants" in r.get("body", "") for r in graphql), "Solver did not query live variants"
    assert any('"after": "2"' in r.get("body", "") or '"after":"2"' in r.get("body", "") for r in graphql), "Solver did not follow GraphQL cursor pagination"
    assert any(r["path"].startswith("/warehouse/stock") for r in records), "Solver did not query warehouse stock"
    assert any(r["path"].startswith("/warehouse/reservations") for r in records), "Solver did not query warehouse reservations"
    assert any(r["path"].startswith("/carrier/track/") for r in records), "Solver did not query carrier tracking"


def test_inputs_and_hidden_service_were_not_modified() -> None:
    server_hash = hashlib.sha256(Path("/services/ecommerce-recon/server.py").read_bytes()).hexdigest()
    expected_server_hash = Path("/opt/ecommerce-recon-server.sha256").read_text(encoding="utf-8").strip()
    assert server_hash == expected_server_hash, "Hidden live service was modified"

    current = subprocess.check_output("find /root/data -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    expected = Path("/opt/ecommerce-recon-data.sha256").read_text(encoding="utf-8")
    assert current == expected, "Input data under /root/data was modified"


def test_live_services_still_healthy() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8123/health", timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "ecommerce-recon"


def test_stale_snapshot_was_not_used_as_sole_source() -> None:
    rows_path = Path("/root/output/fulfillment_exceptions.csv")
    text = rows_path.read_text(encoding="utf-8")
    assert "#H1008" in text, "The live-only order #H1008 is missing, suggesting stale snapshot dependence"
    assert "gid://shopify/LineItem/9009" in text, "The live-only HAT-CANVAS line item is missing"
