import csv
from pathlib import Path


OUTPUT = Path("/root/dns_beacon_clusters.csv")
PCAP = Path("/root/pcaps/dns_resolver_mix.pcap")

EXPECTED_ROWS = [
    {
        "src_host": "10.42.0.19",
        "suspicious_base_domain": "backupsync.net",
        "query_count": "5",
        "longest_query_name_len": "67",
        "first_seen_utc": "2025-02-11T14:22:10Z",
    },
    {
        "src_host": "10.42.0.44",
        "suspicious_base_domain": "telemetry-cdn.org",
        "query_count": "4",
        "longest_query_name_len": "66",
        "first_seen_utc": "2025-02-11T14:31:40Z",
    },
]

EXPECTED_FIELDS = [
    "src_host",
    "suspicious_base_domain",
    "query_count",
    "longest_query_name_len",
    "first_seen_utc",
]


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with OUTPUT.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames or [], list(reader)


def test_pcap_exists() -> None:
    assert PCAP.exists(), "dns_resolver_mix.pcap is missing"


def test_output_exists() -> None:
    assert OUTPUT.exists(), "dns_beacon_clusters.csv is missing"


def test_csv_header_matches_expected() -> None:
    fieldnames, _ = load_rows()
    assert fieldnames == EXPECTED_FIELDS


def test_csv_rows_match_expected() -> None:
    _, rows = load_rows()
    assert rows == EXPECTED_ROWS


def test_only_two_clusters_are_reported() -> None:
    _, rows = load_rows()
    assert len(rows) == 2


def test_rows_are_sorted_by_first_seen_then_src_host() -> None:
    _, rows = load_rows()
    sorted_rows = sorted(rows, key=lambda row: (row["first_seen_utc"], row["src_host"]))
    assert rows == sorted_rows


def test_query_counts_are_numeric_and_large_enough() -> None:
    _, rows = load_rows()
    counts = [int(row["query_count"]) for row in rows]
    assert counts == [5, 4]
    assert all(count >= 4 for count in counts)


def test_longest_query_lengths_are_numeric_and_suspicious() -> None:
    _, rows = load_rows()
    lengths = [int(row["longest_query_name_len"]) for row in rows]
    assert lengths == [67, 66]
    assert all(length >= 45 for length in lengths)


def test_base_domains_match_expected_candidates() -> None:
    _, rows = load_rows()
    assert [row["suspicious_base_domain"] for row in rows] == ["backupsync.net", "telemetry-cdn.org"]


def test_first_seen_values_use_utc_zulu_format() -> None:
    _, rows = load_rows()
    assert all(row["first_seen_utc"].endswith("Z") for row in rows)
    assert all("T" in row["first_seen_utc"] for row in rows)
