#!/bin/bash
set -euo pipefail

python3 <<'PY'
import csv
import json
import shutil
import subprocess
from pathlib import Path


MANIFEST = Path("/root/data/transfer1_ticket_manifest.json")
WEIGHTS = Path("/root/data/transfer1_score_weights.json")
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/local.rules")
OUTPUT = Path("/root/transfer1_incident_queue.csv")
TMP_ROOT = Path("/tmp/transfer1_queue")


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

    sids = []
    eve_path = log_dir / "eve.json"
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
weights = {int(key): int(value) for key, value in json.loads(WEIGHTS.read_text()).items()}
rows = []

for ticket in manifest["tickets"]:
    sids = run_suricata(ticket["pcap"])
    unique_sids = sorted(set(sids))
    weighted_score = sum(weights.get(sid, 0) for sid in sids)
    if weighted_score >= 12:
        queue_status = "critical"
    elif weighted_score >= 1:
        queue_status = "review"
    else:
        queue_status = "clear"

    rows.append(
        {
            "ticket_id": ticket["ticket_id"],
            "pcap": ticket["pcap"],
            "owner": ticket["owner"],
            "environment": ticket["environment"],
            "alert_count": str(len(sids)),
            "signature_ids": "|".join(str(sid) for sid in unique_sids),
            "weighted_score": str(weighted_score),
            "queue_status": queue_status,
        }
    )

rows.sort(key=lambda item: (-int(item["weighted_score"]), item["ticket_id"]))

with OUTPUT.open("w", newline="") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "ticket_id",
            "pcap",
            "owner",
            "environment",
            "alert_count",
            "signature_ids",
            "weighted_score",
            "queue_status",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
PY
