import csv
import json
import shutil
import subprocess
from pathlib import Path


OUTPUT = Path("/root/transfer1_incident_queue.csv")
MANIFEST = Path("/root/data/transfer1_ticket_manifest.json")
WEIGHTS = Path("/root/data/transfer1_score_weights.json")
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/local.rules")
TMP_ROOT = Path("/tmp/transfer1_test_runs")


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
    assert proc.returncode == 0, f"Suricata failed on {pcap_name}:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

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


def build_expected_rows() -> list[dict]:
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
    return rows


def test_output_file_exists():
    assert OUTPUT.exists(), "Expected /root/transfer1_incident_queue.csv to exist"


def test_csv_matches_runtime_alerts():
    with OUTPUT.open(newline="") as fh:
        actual_rows = list(csv.DictReader(fh))
    expected_rows = build_expected_rows()
    assert actual_rows == expected_rows


if __name__ == "__main__":
    test_output_file_exists()
    test_csv_matches_runtime_alerts()
