import json
import subprocess
import tempfile
from pathlib import Path

ANSWER_FILE = Path("/root/answer/rulepack-benchmark.json")
BASE_DIR = Path("/root/rulepack-benchmark")
PCAPS_DIR = BASE_DIR / "pcaps"
RULEPACKS_DIR = BASE_DIR / "rulepacks"
SURICATA_CONFIG = BASE_DIR / "suricata.yaml"
LABELS_FILE = BASE_DIR / "labels.json"


def load_answer() -> dict:
    assert ANSWER_FILE.exists(), "answer/rulepack-benchmark.json does not exist"
    return json.loads(ANSWER_FILE.read_text())


def load_labels() -> dict[str, str]:
    data = json.loads(LABELS_FILE.read_text())
    assert isinstance(data, dict) and "samples" in data, "labels.json must contain a samples array"
    labels = {}
    for item in data["samples"]:
        assert isinstance(item, dict), "labels.json samples must contain objects"
        assert set(item) == {"pcap", "label"}, "labels.json samples must contain only pcap and label"
        assert item["label"] in {"exfil", "benign"}, "labels must be exfil or benign"
        labels[item["pcap"]] = item["label"]
    return labels


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


def expected_output() -> dict:
    labels = load_labels()
    pcap_names = sorted(labels)
    rows = []

    for rule_path in sorted(RULEPACKS_DIR.glob("*.rules")):
        tp = 0
        fp = 0
        fn = 0
        samples = []

        for pcap_name in pcap_names:
            with tempfile.TemporaryDirectory(prefix=f"verify-{rule_path.stem}-") as tmpdir:
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
                assert proc.returncode == 0, (
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

            samples.append(
                {
                    "pcap": pcap_name,
                    "label": label,
                    "predicted": predicted,
                    "alert_count": len(sids),
                    "matched_sids": sorted(set(sids)),
                }
            )

        precision, recall, f1 = rounded_metrics(tp, fp, fn)
        rows.append(
            {
                "rulepack": rule_path.name,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "samples": samples,
            }
        )

    winner = min(rows, key=lambda item: (-item["f1"], -item["precision"], item["fp"], item["rulepack"]))["rulepack"]
    return {"metric": "f1", "winner": winner, "rulepacks": rows}


def test_schema_and_contract() -> None:
    data = load_answer()
    labels = load_labels()
    expected_rulepacks = sorted(path.name for path in RULEPACKS_DIR.glob("*.rules"))
    expected_pcaps = sorted(labels)

    assert set(data) == {"metric", "winner", "rulepacks"}, "top-level fields must be metric, winner, rulepacks"
    assert data["metric"] == "f1", "metric must be f1"
    assert isinstance(data["winner"], str) and data["winner"], "winner must be a non-empty string"
    assert isinstance(data["rulepacks"], list), "rulepacks must be a list"

    actual_rulepacks = []
    for rulepack in data["rulepacks"]:
        assert isinstance(rulepack, dict), "each rulepack entry must be an object"
        assert set(rulepack) == {"rulepack", "tp", "fp", "fn", "precision", "recall", "f1", "samples"}, "unexpected rulepack fields"
        assert isinstance(rulepack["rulepack"], str) and rulepack["rulepack"], "rulepack must be a non-empty string"
        assert isinstance(rulepack["tp"], int) and rulepack["tp"] >= 0, "tp must be a non-negative integer"
        assert isinstance(rulepack["fp"], int) and rulepack["fp"] >= 0, "fp must be a non-negative integer"
        assert isinstance(rulepack["fn"], int) and rulepack["fn"] >= 0, "fn must be a non-negative integer"
        assert isinstance(rulepack["precision"], (int, float)), "precision must be numeric"
        assert isinstance(rulepack["recall"], (int, float)), "recall must be numeric"
        assert isinstance(rulepack["f1"], (int, float)), "f1 must be numeric"
        assert isinstance(rulepack["samples"], list), "samples must be a list"

        sample_names = []
        for sample in rulepack["samples"]:
            assert isinstance(sample, dict), "each sample entry must be an object"
            assert set(sample) == {"pcap", "label", "predicted", "alert_count", "matched_sids"}, "unexpected sample fields"
            assert isinstance(sample["pcap"], str) and sample["pcap"], "pcap must be a non-empty string"
            assert sample["label"] in {"exfil", "benign"}, "label must be exfil or benign"
            assert sample["predicted"] in {"exfil", "benign"}, "predicted must be exfil or benign"
            assert isinstance(sample["alert_count"], int) and sample["alert_count"] >= 0, "alert_count must be a non-negative integer"
            assert isinstance(sample["matched_sids"], list), "matched_sids must be a list"
            assert sample["matched_sids"] == sorted(sample["matched_sids"]), "matched_sids must be ascending"
            assert len(sample["matched_sids"]) == len(set(sample["matched_sids"])), "matched_sids must be deduplicated"
            assert all(isinstance(value, int) for value in sample["matched_sids"]), "matched_sids must contain integers"
            if sample["alert_count"] == 0:
                assert sample["predicted"] == "benign", "predicted must be benign when alert_count is 0"
            else:
                assert sample["predicted"] == "exfil", "predicted must be exfil when alert_count is greater than 0"
            sample_names.append(sample["pcap"])

        assert sample_names == expected_pcaps, "samples must cover every labeled pcap exactly once and stay sorted"
        actual_rulepacks.append(rulepack["rulepack"])

    assert actual_rulepacks == expected_rulepacks, "rulepacks must cover every candidate rules file and stay sorted"
    assert data["winner"] in actual_rulepacks, "winner must name one of the provided rulepacks"


def test_output_matches_independent_benchmark() -> None:
    assert load_answer() == expected_output()
