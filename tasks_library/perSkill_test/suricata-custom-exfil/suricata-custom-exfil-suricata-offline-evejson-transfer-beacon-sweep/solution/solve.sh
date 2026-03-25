#!/bin/bash
set -euo pipefail

mkdir -p /root/answer

python3 <<'PY'
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

PCAPS_DIR = Path("/root/beacon-sweep/pcaps")
SURICATA_CONFIG = Path("/root/beacon-sweep/suricata.yaml")
RULES_FILE = Path("/root/beacon-sweep/beacon.rules")
OUTPUT_FILE = Path("/root/answer/beacon-sweep.json")


def parse_alert_sids(eve_path: Path) -> list[int]:
    if not eve_path.exists():
        return []

    sids = []
    for line in eve_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") != "alert":
            continue
        sid = (event.get("alert") or {}).get("signature_id")
        if isinstance(sid, int):
            sids.append(sid)
    return sids


samples = []
for pcap_path in sorted(PCAPS_DIR.glob("*.pcap")):
    log_dir = Path(tempfile.mkdtemp(prefix=f"suri-{pcap_path.stem}-"))
    try:
        proc = subprocess.run(
            [
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
                str(pcap_path),
                "-l",
                str(log_dir),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            raise SystemExit(
                f"Suricata failed on {pcap_path.name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        sids = parse_alert_sids(log_dir / "eve.json")
        samples.append(
            {
                "pcap": pcap_path.name,
                "matched_sids": sorted(set(sids)),
                "alert_count": len(sids),
                "classification": "infected" if sids else "clean",
            }
        )
    finally:
        shutil.rmtree(log_dir, ignore_errors=True)

OUTPUT_FILE.write_text(json.dumps({"samples": samples}, indent=2) + "\n")
PY
