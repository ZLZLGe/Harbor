#!/bin/bash
set -euo pipefail

mkdir -p /root/answer

python3 <<'PY'
import json
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = Path("/root/rulepack-benchmark")
PCAPS_DIR = BASE_DIR / "pcaps"
RULEPACKS_DIR = BASE_DIR / "rulepacks"
SURICATA_CONFIG = BASE_DIR / "suricata.yaml"
LABELS_FILE = BASE_DIR / "labels.json"
OUTPUT_FILE = Path("/root/answer/rulepack-benchmark.json")


def parse_alert_sids(eve_path: Path) -> list[int]:
    if not eve_path.exists():
        return []

    sids = []
    for line in eve_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        if event.get("event_type") != "alert":
            continue
        sid = (event.get("alert") or {}).get("signature_id")
        if isinstance(sid, int):
            sids.append(sid)
    return sids


def rounded_metrics(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return round(precision, 6), round(recall, 6), round(f1, 6)


labels_data = json.loads(LABELS_FILE.read_text())
labels = {item["pcap"]: item["label"] for item in labels_data["samples"]}
pcap_names = sorted(labels)

rulepack_rows = []
for rule_path in sorted(RULEPACKS_DIR.glob("*.rules")):
    sample_rows = []
    tp = 0
    fp = 0
    fn = 0

    for pcap_name in pcap_names:
        with tempfile.TemporaryDirectory(prefix=f"{rule_path.stem}-") as tmpdir:
            proc = subprocess.run(
                [
                    "suricata",
                    "--runmode",
                    "single",
                    "-c",
                    str(SURICATA_CONFIG),
                    "-S",
                    str(rule_path),
                    "-k",
                    "none",
                    "-r",
                    str(PCAPS_DIR / pcap_name),
                    "-l",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if proc.returncode != 0:
                raise SystemExit(
                    f"Suricata failed on {pcap_name} with {rule_path.name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
                )
            sids = parse_alert_sids(Path(tmpdir) / "eve.json")

        label = labels[pcap_name]
        predicted = "exfil" if sids else "benign"

        if label == "exfil" and predicted == "exfil":
            tp += 1
        elif label == "benign" and predicted == "exfil":
            fp += 1
        elif label == "exfil" and predicted == "benign":
            fn += 1

        sample_rows.append(
            {
                "pcap": pcap_name,
                "label": label,
                "predicted": predicted,
                "alert_count": len(sids),
                "matched_sids": sorted(set(sids)),
            }
        )

    precision, recall, f1 = rounded_metrics(tp, fp, fn)
    rulepack_rows.append(
        {
            "rulepack": rule_path.name,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "samples": sample_rows,
        }
    )

winner = min(rulepack_rows, key=lambda item: (-item["f1"], -item["precision"], item["fp"], item["rulepack"]))["rulepack"]

OUTPUT_FILE.write_text(
    json.dumps(
        {
            "metric": "f1",
            "winner": winner,
            "rulepacks": rulepack_rows,
        },
        indent=2,
    )
    + "\n"
)
PY
