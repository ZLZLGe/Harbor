import csv
import json
import subprocess
import tempfile
from pathlib import Path

ANSWER_FILE = Path("/root/answer/lateral-timeline.csv")
PCAP_FILE = Path("/root/lateral-timeline/ops-east-long.pcap")
SURICATA_CONFIG = Path("/root/lateral-timeline/suricata.yaml")
RULES_FILE = Path("/root/lateral-timeline/lateral.rules")
EXPECTED_FIELDS = ["timestamp", "sid", "src_ip", "dest_ip", "signature"]


def load_answer_rows() -> list[dict[str, str]]:
    assert ANSWER_FILE.exists(), "answer/lateral-timeline.csv does not exist"
    with ANSWER_FILE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == EXPECTED_FIELDS, "CSV header must be timestamp,sid,src_ip,dest_ip,signature"
        return list(reader)


def compute_expected_rows() -> list[dict[str, str]]:
    log_dir = Path(tempfile.mkdtemp(prefix="verify-lateral-"))
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
            str(PCAP_FILE),
            "-l",
            str(log_dir),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, f"Suricata failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    rows_by_sid: dict[int, dict[str, str]] = {}
    eve_path = log_dir / "eve.json"
    assert eve_path.exists(), "eve.json was not produced"

    for line in eve_path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "alert":
            continue
        alert = event.get("alert") or {}
        signature = alert.get("signature")
        sid = alert.get("signature_id")
        if not isinstance(signature, str) or not signature.startswith("[first-wave] "):
            continue
        assert isinstance(sid, int), "alert.signature_id must be an integer"
        row = {
            "timestamp": event["timestamp"],
            "sid": str(sid),
            "src_ip": event["src_ip"],
            "dest_ip": event["dest_ip"],
            "signature": signature,
        }
        current = rows_by_sid.get(sid)
        if current is None or (row["timestamp"], int(row["sid"])) < (current["timestamp"], int(current["sid"])):
            rows_by_sid[sid] = row

    return sorted(rows_by_sid.values(), key=lambda item: (item["timestamp"], int(item["sid"])))


def test_csv_schema_and_sorting() -> None:
    rows = load_answer_rows()
    assert rows, "CSV must contain at least one data row"

    seen_sids = set()
    ordering = []
    for row in rows:
        assert list(row.keys()) == EXPECTED_FIELDS, "unexpected CSV columns"
        assert row["timestamp"], "timestamp must be non-empty"
        assert row["src_ip"], "src_ip must be non-empty"
        assert row["dest_ip"], "dest_ip must be non-empty"
        assert row["signature"].startswith("[first-wave] "), "signature must come from first-wave alerts"
        sid = int(row["sid"])
        assert sid not in seen_sids, "each sid must appear only once"
        seen_sids.add(sid)
        ordering.append((row["timestamp"], sid))

    assert ordering == sorted(ordering), "rows must be sorted by timestamp, then sid"


def test_csv_matches_independent_suricata_timeline() -> None:
    assert load_answer_rows() == compute_expected_rows()
