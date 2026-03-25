import csv
from pathlib import Path


INPUT_FILE = Path("/root/gateway_tenant_profiles.tsv")
OUTPUT_FILE = Path("/root/gateway_escalations.csv")
THREAT_ORDER = ("port_scan", "dos_pattern", "beaconing")
PRIORITY_ORDER = ("critical", "high", "medium", "low")


def load_input_rows():
    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile, delimiter="\t"))


def load_output_rows():
    with open(OUTPUT_FILE, "r", encoding="utf-8", newline="") as outfile:
        return list(csv.DictReader(outfile))


def detect_flags(row):
    port_scan = (
        float(row["dst_port_entropy"]) > 6.0
        and float(row["syn_probe_ratio"]) > 0.7
        and int(row["distinct_external_ports"]) > 100
    )
    baseline = float(row["rpm_baseline"])
    dos_pattern = False if baseline == 0 else (float(row["rpm_peak"]) / baseline) > 20
    beaconing = float(row["checkin_iat_cv"]) < 0.5
    return {
        "port_scan": port_scan,
        "dos_pattern": dos_pattern,
        "beaconing": beaconing,
    }


def threat_labels(flags):
    active = [name for name in THREAT_ORDER if flags[name]]
    return ";".join(active) if active else "benign"


def priority_for(flags):
    if flags["port_scan"] and flags["dos_pattern"]:
        return "critical"
    if flags["port_scan"] or (flags["dos_pattern"] and flags["beaconing"]):
        return "high"
    if flags["dos_pattern"] or flags["beaconing"]:
        return "medium"
    return "low"


def queue_for(flags):
    if flags["port_scan"]:
        return "tenant-abuse"
    if flags["dos_pattern"]:
        return "traffic-surge"
    if flags["beaconing"]:
        return "signal-review"
    return "baseline-monitoring"


def expected_rows():
    rows = []
    for input_row in load_input_rows():
        flags = detect_flags(input_row)
        rows.append(
            {
                "tenant_id": input_row["tenant_id"],
                "threat_labels": threat_labels(flags),
                "priority": priority_for(flags),
                "dispatch_queue": queue_for(flags),
            }
        )

    priority_rank = {name: index for index, name in enumerate(PRIORITY_ORDER)}
    rows.sort(key=lambda row: (priority_rank[row["priority"]], row["tenant_id"]))
    return rows


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), "Missing /root/gateway_escalations.csv"


def test_header_and_row_count():
    output_rows = load_output_rows()
    expected = expected_rows()

    assert len(output_rows) == len(expected), "Output must contain one row per tenant"
    assert list(output_rows[0].keys()) == [
        "tenant_id",
        "threat_labels",
        "priority",
        "dispatch_queue",
    ], "Output must use the exact required header"


def test_rows_match_expected_values_and_order():
    assert load_output_rows() == expected_rows()


def test_priority_ordering_is_monotonic():
    output_rows = load_output_rows()
    priority_rank = {name: index for index, name in enumerate(PRIORITY_ORDER)}
    observed = [priority_rank[row["priority"]] for row in output_rows]
    assert observed == sorted(observed), "Rows must be sorted by the required priority order"


def test_queue_assignment_matches_threat_labels():
    for row in load_output_rows():
        labels = [] if row["threat_labels"] == "benign" else row["threat_labels"].split(";")

        if "port_scan" in labels:
            assert row["dispatch_queue"] == "tenant-abuse"
        elif "dos_pattern" in labels:
            assert row["dispatch_queue"] == "traffic-surge"
        elif "beaconing" in labels:
            assert row["dispatch_queue"] == "signal-review"
        else:
            assert row["dispatch_queue"] == "baseline-monitoring"
