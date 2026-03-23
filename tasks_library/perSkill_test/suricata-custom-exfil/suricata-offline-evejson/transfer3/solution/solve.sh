#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import shutil
import subprocess
from pathlib import Path


MANIFEST = Path("/root/data/transfer3_capture_manifest.json")
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
CURRENT_RULES = Path("/root/rules/current.rules")
CANDIDATE_RULES = Path("/root/rules/candidate.rules")
OUTPUT = Path("/root/transfer3_rule_regression_report.json")
TMP_ROOT = Path("/tmp/transfer3_compare")


def run_suricata(pcap_name: str, rules_path: Path, log_name: str) -> list[int]:
    log_dir = TMP_ROOT / log_name / Path(pcap_name).stem
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
        str(rules_path),
        "-k",
        "none",
        "-r",
        str(PCAPS_DIR / pcap_name),
        "-l",
        str(log_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Suricata failed for {pcap_name} with {rules_path.name}:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

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
results = []
candidate_only_union = set()
pcaps_with_new_alerts = []

for item in manifest["captures"]:
    current_sids = run_suricata(item["pcap"], CURRENT_RULES, "current")
    candidate_sids = run_suricata(item["pcap"], CANDIDATE_RULES, "candidate")
    current_unique = sorted(set(current_sids))
    candidate_unique = sorted(set(candidate_sids))
    new_signature_ids = sorted(set(candidate_unique) - set(current_unique))
    if new_signature_ids:
        candidate_only_union.update(new_signature_ids)
        pcaps_with_new_alerts.append(item["pcap"])
        regression_flag = "expanded"
    else:
        regression_flag = "unchanged"

    results.append(
        {
            "pcap": item["pcap"],
            "owner": item["owner"],
            "current_alert_count": len(current_sids),
            "candidate_alert_count": len(candidate_sids),
            "current_signature_ids": current_unique,
            "candidate_signature_ids": candidate_unique,
            "new_signature_ids": new_signature_ids,
            "regression_flag": regression_flag,
        }
    )

output = {
    "comparison_id": manifest["comparison_id"],
    "results": results,
    "candidate_only_signatures": sorted(candidate_only_union),
    "pcaps_with_new_alerts": pcaps_with_new_alerts,
    "safe_to_promote": len(candidate_only_union) == 0,
}

OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
PY
