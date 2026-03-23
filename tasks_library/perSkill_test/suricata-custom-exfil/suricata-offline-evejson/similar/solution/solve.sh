#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import shutil
import subprocess
from pathlib import Path


MANIFEST = Path("/root/data/similar_batch_manifest.json")
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/local.rules")
OUTPUT = Path("/root/similar_alert_digest.json")
TMP_ROOT = Path("/tmp/similar_alert_digest")


def run_suricata(pcap_name: str) -> list[int]:
    log_dir = TMP_ROOT / Path(pcap_name).stem
    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "suricata",
        "--runmode",
        "single",
        "-c",
        str(SURICATA_CONFIG),
        "-S",
        str(RULES_FILE),
        "-k",
        "none",
        "-r",
        str(PCAPS_DIR / pcap_name),
        "-l",
        str(log_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Suricata failed for {pcap_name}:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

    eve_path = log_dir / "eve.json"
    sids = []
    if eve_path.exists():
        for line in eve_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("event_type") != "alert":
                continue
            sid = (record.get("alert") or {}).get("signature_id")
            if isinstance(sid, int):
                sids.append(sid)
    return sids


manifest = json.loads(MANIFEST.read_text())
results = []
total_alerts = 0
alerted_pcaps = 0
page_count = 0

for item in manifest["captures"]:
    sids = run_suricata(item["pcap"])
    total_alerts += len(sids)
    if sids:
        alerted_pcaps += 1

    unique_sids = sorted(set(sids))
    if 1000001 in unique_sids:
        status = "confirmed-exfil"
        escalation = "page"
        page_count += 1
    elif 1000002 in unique_sids:
        status = "staging-activity"
        escalation = "review"
    else:
        status = "clean"
        escalation = "none"

    results.append(
        {
            "pcap": item["pcap"],
            "site": item["site"],
            "alert_count": len(sids),
            "signature_ids": unique_sids,
            "status": status,
            "escalation": escalation,
        }
    )

output = {
    "batch_id": manifest["batch_id"],
    "results": results,
    "totals": {
        "pcap_count": len(results),
        "alerted_pcaps": alerted_pcaps,
        "page_count": page_count,
        "total_alerts": total_alerts,
    },
}

OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
PY
