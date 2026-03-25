import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ANSWER_FILE = Path("/root/answer/beacon-sweep.json")
PCAPS_DIR = Path("/root/beacon-sweep/pcaps")
SURICATA_CONFIG = Path("/root/beacon-sweep/suricata.yaml")
RULES_FILE = Path("/root/beacon-sweep/beacon.rules")


def load_answer() -> dict:
    assert ANSWER_FILE.exists(), "answer/beacon-sweep.json does not exist"
    return json.loads(ANSWER_FILE.read_text())


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


def expected_samples() -> list[dict]:
    rows = []
    for pcap_path in sorted(PCAPS_DIR.glob("*.pcap")):
        log_dir = Path(tempfile.mkdtemp(prefix=f"verify-{pcap_path.stem}-"))
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
            assert proc.returncode == 0, (
                f"Suricata failed on {pcap_path.name}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
            sids = parse_alert_sids(log_dir / "eve.json")
            rows.append(
                {
                    "pcap": pcap_path.name,
                    "matched_sids": sorted(set(sids)),
                    "alert_count": len(sids),
                    "classification": "infected" if sids else "clean",
                }
            )
        finally:
            shutil.rmtree(log_dir, ignore_errors=True)
    return rows


def test_output_schema_and_inventory() -> None:
    data = load_answer()
    assert isinstance(data, dict), "top-level output must be a JSON object"
    assert "samples" in data, "top-level output must include samples"

    samples = data["samples"]
    assert isinstance(samples, list), "samples must be a list"

    expected_names = sorted(path.name for path in PCAPS_DIR.glob("*.pcap"))
    actual_names = []
    for sample in samples:
        assert isinstance(sample, dict), "each sample must be an object"
        assert set(sample) == {"pcap", "matched_sids", "alert_count", "classification"}, "unexpected sample fields"
        assert isinstance(sample["pcap"], str) and sample["pcap"], "pcap must be a non-empty string"
        assert isinstance(sample["matched_sids"], list), "matched_sids must be a list"
        assert sample["matched_sids"] == sorted(sample["matched_sids"]), "matched_sids must be ascending"
        assert len(sample["matched_sids"]) == len(set(sample["matched_sids"])), "matched_sids must be deduplicated"
        assert all(isinstance(value, int) for value in sample["matched_sids"]), "matched_sids must contain integers"
        assert isinstance(sample["alert_count"], int) and sample["alert_count"] >= 0, "alert_count must be a non-negative integer"
        assert sample["classification"] in {"infected", "clean"}, "classification must be infected or clean"
        if sample["alert_count"] == 0:
            assert sample["classification"] == "clean"
        else:
            assert sample["classification"] == "infected"
        actual_names.append(sample["pcap"])

    assert actual_names == expected_names, "samples must cover every pcap exactly once and stay sorted"


def test_output_matches_independent_suricata_summary() -> None:
    data = load_answer()
    assert data["samples"] == expected_samples()
