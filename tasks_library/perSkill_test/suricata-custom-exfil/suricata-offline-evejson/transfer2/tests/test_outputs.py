import json
import shutil
import subprocess
from pathlib import Path


OUTPUT = Path("/root/transfer2_rule_budget_audit.json")
MANIFEST = Path("/root/data/transfer2_site_manifest.json")
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/local.rules")
TMP_ROOT = Path("/tmp/transfer2_test_runs")


def run_suricata(pcap_name: str) -> int:
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

    alert_count = 0
    eve_path = log_dir / "eve.json"
    if eve_path.exists():
        for line in eve_path.read_text(errors="replace").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("event_type") == "alert":
                alert_count += 1
    return alert_count


def build_expected() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    site_results = []
    sites_passing = []
    sites_failing = []
    highest_volume_site = None
    highest_alert_count = -1

    for site in manifest["sites"]:
        observed_alerts = sum(run_suricata(pcap_name) for pcap_name in site["captures"])
        status = "pass" if observed_alerts <= site["max_allowed_alerts"] else "fail"
        site_results.append(
            {
                "site": site["site"],
                "captures": site["captures"],
                "max_allowed_alerts": site["max_allowed_alerts"],
                "observed_alerts": observed_alerts,
                "status": status,
            }
        )
        if status == "pass":
            sites_passing.append(site["site"])
        else:
            sites_failing.append(site["site"])
        if observed_alerts > highest_alert_count:
            highest_alert_count = observed_alerts
            highest_volume_site = site["site"]

    return {
        "audit_window": manifest["audit_window"],
        "site_results": site_results,
        "sites_passing": sites_passing,
        "sites_failing": sites_failing,
        "highest_volume_site": highest_volume_site,
    }


def test_output_file_exists():
    assert OUTPUT.exists(), "Expected /root/transfer2_rule_budget_audit.json to exist"


def test_audit_matches_runtime_alert_counts():
    actual = json.loads(OUTPUT.read_text())
    expected = build_expected()
    assert actual == expected


if __name__ == "__main__":
    test_output_file_exists()
    test_audit_matches_runtime_alert_counts()
