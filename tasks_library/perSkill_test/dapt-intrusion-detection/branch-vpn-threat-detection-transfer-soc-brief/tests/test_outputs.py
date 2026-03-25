import csv
import re
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path("/root/branch_vpn_hourly_features.csv")
OUTPUT_FILE = Path("/root/branch_soc_report.md")
THREAT_ORDER = ("port_scan", "dos_pattern", "beaconing")


def load_rows():
    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as infile:
        return list(csv.DictReader(infile))


def detect_flags(row):
    has_port_scan = (
        float(row["port_entropy"]) > 6.0
        and float(row["syn_only_ratio"]) > 0.7
        and int(row["unique_destination_ports"]) > 100
    )
    avg = float(row["packets_per_minute_avg"])
    has_dos = False if avg == 0 else (float(row["packets_per_minute_max"]) / avg) > 20
    has_beaconing = float(row["iat_cv"]) < 0.5
    return {
        "port_scan": has_port_scan,
        "dos_pattern": has_dos,
        "beaconing": has_beaconing,
    }


def dos_ratio(row):
    avg = float(row["packets_per_minute_avg"])
    if avg == 0:
        return 0.0
    return float(row["packets_per_minute_max"]) / avg


def expected_report():
    sites = defaultdict(list)
    for row in load_rows():
        row["flags"] = detect_flags(row)
        sites[row["site_code"]].append(row)

    escalated = []
    for site_code, site_rows in sites.items():
        region = site_rows[0]["region"]
        triggered = [
            threat
            for threat in THREAT_ORDER
            if any(row["flags"][threat] for row in site_rows)
        ]
        if not triggered:
            continue

        evidence = {}
        for threat in triggered:
            matched = [row for row in site_rows if row["flags"][threat]]
            if threat == "port_scan":
                matched.sort(key=lambda row: (-float(row["port_entropy"]), row["hour_utc"]))
            elif threat == "dos_pattern":
                matched.sort(key=lambda row: (-dos_ratio(row), row["hour_utc"]))
            else:
                matched.sort(key=lambda row: (float(row["iat_cv"]), row["hour_utc"]))
            evidence[threat] = matched[0]

        escalated.append(
            {
                "site_code": site_code,
                "region": region,
                "triggered": triggered,
                "evidence": evidence,
            }
        )

    escalated.sort(key=lambda item: item["site_code"])

    summary_lines = [
        f'- Total sites analyzed: {len(sites)}',
        f'- Sites requiring escalation: {len(escalated)}',
        f'- Sites with port_scan evidence: {sum(1 for item in escalated if "port_scan" in item["triggered"])}',
        f'- Sites with dos_pattern evidence: {sum(1 for item in escalated if "dos_pattern" in item["triggered"])}',
        f'- Sites with beaconing evidence: {sum(1 for item in escalated if "beaconing" in item["triggered"])}',
    ]

    site_expectations = {}
    for item in escalated:
        evidence_lines = []
        for threat in item["triggered"]:
            row = item["evidence"][threat]
            if threat == "port_scan":
                evidence_lines.append(
                    (
                        f'- port_scan evidence: {row["hour_utc"]} | '
                        f'port_entropy={row["port_entropy"]} (> 6.0), '
                        f'syn_only_ratio={row["syn_only_ratio"]} (> 0.7), '
                        f'unique_destination_ports={row["unique_destination_ports"]} (> 100)'
                    )
                )
            elif threat == "dos_pattern":
                evidence_lines.append(
                    (
                        f'- dos_pattern evidence: {row["hour_utc"]} | '
                        f'packets_per_minute_max/avg={dos_ratio(row):.2f} using '
                        f'{row["packets_per_minute_max"]}/{row["packets_per_minute_avg"]} (> 20)'
                    )
                )
            else:
                evidence_lines.append(
                    f'- beaconing evidence: {row["hour_utc"]} | iat_cv={row["iat_cv"]} (< 0.5)'
                )

        site_expectations[item["site_code"]] = {
            "heading": f'### {item["site_code"]} ({item["region"]})',
            "trigger_line": f'- Triggered threats: {", ".join(item["triggered"])}',
            "evidence_lines": evidence_lines,
        }

    return summary_lines, escalated, site_expectations


def load_output_lines():
    return OUTPUT_FILE.read_text(encoding="utf-8").splitlines()


def site_blocks(lines):
    blocks = {}
    current_site = None
    for line in lines:
        if line.startswith("### "):
            match = re.fullmatch(r"### ([^ ]+) \((.+)\)", line)
            assert match, "Site headings must use the exact required format"
            current_site = match.group(1)
            blocks[current_site] = [line]
        elif current_site is not None:
            blocks[current_site].append(line)
    return blocks


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), "Missing /root/branch_soc_report.md"


def test_top_level_sections_and_summary_lines():
    lines = load_output_lines()
    expected_summary_lines, _, _ = expected_report()

    assert lines[0] == "# Branch VPN SOC Brief"
    assert "## Global Summary" in lines
    assert "## Escalated Sites" in lines

    summary_index = lines.index("## Global Summary")
    actual_summary = lines[summary_index + 1 : summary_index + 6]
    assert actual_summary == expected_summary_lines


def test_only_escalated_sites_are_listed_in_sorted_order():
    lines = load_output_lines()
    _, escalated, expectations = expected_report()
    headings = [line for line in lines if line.startswith("### ")]

    assert headings == [expectations[item["site_code"]]["heading"] for item in escalated]


def test_site_sections_match_triggered_threats_and_evidence():
    lines = load_output_lines()
    _, escalated, expectations = expected_report()
    blocks = site_blocks(lines)

    assert set(blocks.keys()) == {item["site_code"] for item in escalated}

    for item in escalated:
        expected = expectations[item["site_code"]]
        block = [line for line in blocks[item["site_code"]] if line]
        assert block[0] == expected["heading"]
        assert block[1] == expected["trigger_line"]
        assert block[2:] == expected["evidence_lines"]


def test_non_escalated_sites_do_not_appear():
    lines = load_output_lines()
    _, escalated, _ = expected_report()
    escalated_sites = {item["site_code"] for item in escalated}
    all_sites = {row["site_code"] for row in load_rows()}

    for site_code in sorted(all_sites - escalated_sites):
        assert not any(line.startswith(f"### {site_code} ") for line in lines)
