import re
from pathlib import Path

REPORT_FILE = Path("/root/iot_beacon_report.md")

EXPECTED_SUMMARY = {
    "Inventoried devices analyzed": "5",
    "Periodic candidate flows": "8",
    "Approved periodic flows": "5",
    "Suspected beacon flows": "3",
    "Devices with suspected beacons": "1",
    "Highest risk device": "edge-hub-01 (192.168.3.30)",
}

EXPECTED_SUSPECTED = [
    {
        "device_id": "edge-hub-01",
        "device_ip": "192.168.3.30",
        "device_role": "gateway",
        "dst_ip": "91.189.89.198",
        "protocol": "UDP",
        "dst_port": "123",
        "packet_count": "9",
        "first_seen_utc": "2019-07-15T21:51:59Z",
        "last_seen_utc": "2019-07-16T03:40:27Z",
        "mean_iat_seconds": "2613.56",
        "iat_cv": "0.5352",
        "classification": "suspected_beacon",
    },
    {
        "device_id": "edge-hub-01",
        "device_ip": "192.168.3.30",
        "device_role": "gateway",
        "dst_ip": "91.189.89.199",
        "protocol": "UDP",
        "dst_port": "123",
        "packet_count": "11",
        "first_seen_utc": "2019-07-15T21:15:23Z",
        "last_seen_utc": "2019-07-16T03:06:09Z",
        "mean_iat_seconds": "2104.60",
        "iat_cv": "0.7689",
        "classification": "suspected_beacon",
    },
    {
        "device_id": "edge-hub-01",
        "device_ip": "192.168.3.30",
        "device_role": "gateway",
        "dst_ip": "91.189.91.157",
        "protocol": "UDP",
        "dst_port": "123",
        "packet_count": "8",
        "first_seen_utc": "2019-07-15T21:51:49Z",
        "last_seen_utc": "2019-07-16T03:05:48Z",
        "mean_iat_seconds": "2691.39",
        "iat_cv": "0.5527",
        "classification": "suspected_beacon",
    },
]

EXPECTED_APPROVED = [
    {
        "device_id": "badge-reader-01",
        "device_ip": "192.168.3.190",
        "device_role": "access-control",
        "dst_ip": "224.0.0.251",
        "protocol": "UDP",
        "dst_port": "5353",
        "packet_count": "7",
        "first_seen_utc": "2019-07-15T21:29:52Z",
        "last_seen_utc": "2019-07-16T03:29:52Z",
        "mean_iat_seconds": "3600.09",
        "iat_cv": "0.0000",
        "classification": "approved_periodic",
    },
    {
        "device_id": "edge-hub-01",
        "device_ip": "192.168.3.30",
        "device_role": "gateway",
        "dst_ip": "91.189.94.4",
        "protocol": "UDP",
        "dst_port": "123",
        "packet_count": "14",
        "first_seen_utc": "2019-07-15T21:17:10Z",
        "last_seen_utc": "2019-07-16T03:05:59Z",
        "mean_iat_seconds": "1609.92",
        "iat_cv": "0.5333",
        "classification": "approved_periodic",
    },
    {
        "device_id": "sensor-temp-01",
        "device_ip": "192.168.3.32",
        "device_role": "temperature-sensor",
        "dst_ip": "224.0.0.251",
        "protocol": "UDP",
        "dst_port": "5353",
        "packet_count": "8",
        "first_seen_utc": "2019-07-15T21:01:11Z",
        "last_seen_utc": "2019-07-16T04:01:12Z",
        "mean_iat_seconds": "3600.04",
        "iat_cv": "0.0000",
        "classification": "approved_periodic",
    },
    {
        "device_id": "sensor-temp-02",
        "device_ip": "192.168.3.33",
        "device_role": "temperature-sensor",
        "dst_ip": "224.0.0.251",
        "protocol": "UDP",
        "dst_port": "5353",
        "packet_count": "7",
        "first_seen_utc": "2019-07-15T21:52:10Z",
        "last_seen_utc": "2019-07-16T03:52:10Z",
        "mean_iat_seconds": "3600.01",
        "iat_cv": "0.0000",
        "classification": "approved_periodic",
    },
    {
        "device_id": "signage-speaker-01",
        "device_ip": "192.168.3.26",
        "device_role": "media-endpoint",
        "dst_ip": "224.0.0.251",
        "protocol": "UDP",
        "dst_port": "5353",
        "packet_count": "15",
        "first_seen_utc": "2019-07-15T21:08:35Z",
        "last_seen_utc": "2019-07-16T04:08:35Z",
        "mean_iat_seconds": "1800.00",
        "iat_cv": "0.7561",
        "classification": "approved_periodic",
    },
]

TABLE_COLUMNS = [
    "device_id",
    "device_ip",
    "device_role",
    "dst_ip",
    "protocol",
    "dst_port",
    "packet_count",
    "first_seen_utc",
    "last_seen_utc",
    "mean_iat_seconds",
    "iat_cv",
    "classification",
]


def parse_summary(lines):
    summary = {}
    for line in lines:
        if line.startswith("- "):
            key, value = line[2:].split(": ", 1)
            summary[key] = value
    return summary


def parse_table(lines):
    rows = []
    for line in lines:
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells == TABLE_COLUMNS:
            continue
        rows.append(dict(zip(TABLE_COLUMNS, cells)))
    return rows


def split_sections(text):
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip().splitlines()
    return sections


def main():
    assert REPORT_FILE.exists(), "missing /root/iot_beacon_report.md"
    text = REPORT_FILE.read_text(encoding="utf-8").strip()
    assert text.startswith("# IoT Beacon Hunt Report"), "wrong title"

    sections = split_sections(text)
    assert set(sections) == {
        "Summary",
        "Suspected Beacon Flows",
        "Approved Periodic Flows",
        "Evidence Summary",
    }, "unexpected sections"

    summary = parse_summary(sections["Summary"])
    assert summary == EXPECTED_SUMMARY, f"summary mismatch: {summary}"

    suspected_rows = parse_table(sections["Suspected Beacon Flows"])
    approved_rows = parse_table(sections["Approved Periodic Flows"])
    assert suspected_rows == EXPECTED_SUSPECTED, f"suspected table mismatch: {suspected_rows}"
    assert approved_rows == EXPECTED_APPROVED, f"approved table mismatch: {approved_rows}"

    evidence_lines = [line for line in sections["Evidence Summary"] if line.startswith("- ")]
    assert len(evidence_lines) == 3, f"expected 3 evidence bullets, got {len(evidence_lines)}"
    assert "91.189.89.198, 91.189.89.199, 91.189.91.157" in evidence_lines[0]
    assert "badge-reader-01, sensor-temp-01, sensor-temp-02, signage-speaker-01" in evidence_lines[1]
    assert "91.189.94.4:123/UDP" in evidence_lines[2]


if __name__ == "__main__":
    main()
