import csv
import json
import os
import re
import subprocess
from collections import defaultdict
from difflib import SequenceMatcher


OUTPUT_FILE = "/root/royalty_reconciliation.json"
DATA_ROOT = os.environ.get("TASK_DATA_ROOT", "/root")
SKILL_ROOT = os.path.join(DATA_ROOT, ".codex", "skills", "fuzzy-name-search", "scripts")

FUND_SEARCH_TERMS = [
    "bridge water assoc",
    "renaissance tech llc",
]

ISSUER_SEARCH_TERMS = [
    "palantir tech",
    "nvidia corp",
    "micro strat",
]

def load_tsv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def run_search(args):
    result = subprocess.run(
        ["python3", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert lines, f"search produced no output: {' '.join(args)}"
    return lines


def normalize(value):
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def best_match(term, choices, key):
    normalized_term = normalize(term)
    ranked = sorted(
        choices,
        key=lambda item: (
            SequenceMatcher(None, normalized_term, normalize(key(item))).ratio(),
            key(item),
        ),
        reverse=True,
    )
    return ranked[0]


def top_fund_match(term):
    try:
        lines = run_search(
            [
                os.path.join(SKILL_ROOT, "search_fund.py"),
                "--keywords",
                term,
                "--quarter",
                "2025-q2",
                "--topk",
                "1",
            ]
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        coverpage_rows = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "COVERPAGE.tsv"))
        return best_match(term, coverpage_rows, lambda item: item["FILINGMANAGER_NAME"])["ACCESSION_NUMBER"]

    fields = {}
    for line in lines:
        if ":" not in line or line.startswith("** Rank"):
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    assert "ACCESSION_NUMBER" in fields, f"unexpected fund search output for {term}: {lines}"
    return fields["ACCESSION_NUMBER"]


def top_stock_match(term):
    try:
        lines = run_search(
            [
                os.path.join(SKILL_ROOT, "search_stock_cusip.py"),
                "--keywords",
                term,
                "--topk",
                "1",
            ]
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        infotable_rows = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "INFOTABLE.tsv"))
        issuer_catalog = {}
        for row in infotable_rows:
            issuer_catalog.setdefault(row["CUSIP"], row["NAMEOFISSUER"])
        issuer_rows = [
            {"CUSIP": cusip, "NAMEOFISSUER": issuer_name}
            for cusip, issuer_name in issuer_catalog.items()
        ]
        return best_match(term, issuer_rows, lambda item: item["NAMEOFISSUER"])["CUSIP"]

    for line in lines:
        if line.startswith("CUSIP:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"unexpected stock search output for {term}: {lines}")


def load_output():
    assert os.path.isfile(OUTPUT_FILE), f"missing output file: {OUTPUT_FILE}"
    with open(OUTPUT_FILE) as handle:
        return json.load(handle)


def compute_expected():
    coverpage_rows = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "COVERPAGE.tsv"))
    infotable_rows = load_tsv(os.path.join(DATA_ROOT, "2025-q2", "INFOTABLE.tsv"))

    coverpage = {row["ACCESSION_NUMBER"]: row for row in coverpage_rows}
    fund_matches = []
    target_accessions = []
    for term in FUND_SEARCH_TERMS:
        accession_number = top_fund_match(term)
        row = coverpage[accession_number]
        target_accessions.append(row["ACCESSION_NUMBER"])
        fund_matches.append(
            {
                "search_term": term,
                "accession_number": row["ACCESSION_NUMBER"],
                "filingmanager_name": row["FILINGMANAGER_NAME"],
                "form13f_file_number": row["FORM13FFILENUMBER"],
            }
        )

    issuer_catalog = {}
    for row in infotable_rows:
        issuer_catalog.setdefault(row["CUSIP"], row["NAMEOFISSUER"])

    issuer_rows = [
        {"CUSIP": cusip, "NAMEOFISSUER": issuer_name}
        for cusip, issuer_name in issuer_catalog.items()
    ]

    issuer_matches = []
    target_cusips = []
    for term in ISSUER_SEARCH_TERMS:
        cusip = top_stock_match(term)
        row = next(item for item in issuer_rows if item["CUSIP"] == cusip)
        target_cusips.append(row["CUSIP"])
        issuer_matches.append(
            {
                "search_term": term,
                "cusip": row["CUSIP"],
                "issuer_name": row["NAMEOFISSUER"],
            }
        )

    issuer_names = {row["CUSIP"]: row["NAMEOFISSUER"] for row in issuer_rows}

    filtered_positions = [
        row
        for row in infotable_rows
        if row["ACCESSION_NUMBER"] in target_accessions and row["CUSIP"] in target_cusips
    ]

    manager_rollup = defaultdict(lambda: {"value": 0, "shares": 0, "cusips": set()})
    duplicate_groups = defaultdict(list)
    for row in filtered_positions:
        accession_number = row["ACCESSION_NUMBER"]
        cusip = row["CUSIP"]
        manager_rollup[accession_number]["value"] += int(row["VALUE_USD"])
        manager_rollup[accession_number]["shares"] += int(row["SSHPRNAMT"])
        manager_rollup[accession_number]["cusips"].add(cusip)
        duplicate_groups[(accession_number, cusip)].append(row["POSITION_ID"])

    manager_exposure_rank = []
    for rank, accession_number in enumerate(
        sorted(manager_rollup, key=lambda item: (-manager_rollup[item]["value"], item)),
        start=1,
    ):
        rollup = manager_rollup[accession_number]
        manager_exposure_rank.append(
            {
                "rank": rank,
                "accession_number": accession_number,
                "filingmanager_name": coverpage[accession_number]["FILINGMANAGER_NAME"],
                "total_value_usd": float(rollup["value"]),
                "total_shares": rollup["shares"],
                "matched_cusips": sorted(rollup["cusips"]),
            }
        )

    duplicate_position_groups = []
    for accession_number, cusip in sorted(duplicate_groups):
        position_ids = sorted(duplicate_groups[(accession_number, cusip)])
        if len(position_ids) <= 1:
            continue
        duplicate_position_groups.append(
            {
                "accession_number": accession_number,
                "filingmanager_name": coverpage[accession_number]["FILINGMANAGER_NAME"],
                "cusip": cusip,
                "issuer_name": issuer_names[cusip],
                "position_ids": position_ids,
                "duplicate_count": len(position_ids),
            }
        )

    largest_position = sorted(
        filtered_positions,
        key=lambda row: (-int(row["VALUE_USD"]), row["ACCESSION_NUMBER"], row["CUSIP"], row["POSITION_ID"]),
    )[0]

    return {
        "fund_matches": fund_matches,
        "issuer_matches": issuer_matches,
        "selected_position_summary": {
            "matched_fund_count": len(fund_matches),
            "matched_issuer_count": len(issuer_matches),
            "selected_position_rows": len(filtered_positions),
            "total_value_usd": float(sum(int(row["VALUE_USD"]) for row in filtered_positions)),
        },
        "manager_exposure_rank": manager_exposure_rank,
        "duplicate_position_groups": duplicate_position_groups,
        "largest_position": {
            "position_id": largest_position["POSITION_ID"],
            "accession_number": largest_position["ACCESSION_NUMBER"],
            "filingmanager_name": coverpage[largest_position["ACCESSION_NUMBER"]]["FILINGMANAGER_NAME"],
            "cusip": largest_position["CUSIP"],
            "issuer_name": issuer_names[largest_position["CUSIP"]],
            "value_usd": float(largest_position["VALUE_USD"]),
            "shares": int(largest_position["SSHPRNAMT"]),
        },
    }


def test_report_matches_expected():
    assert load_output() == compute_expected()


def test_schema_and_internal_consistency():
    data = load_output()

    assert set(data.keys()) == {
        "fund_matches",
        "issuer_matches",
        "selected_position_summary",
        "manager_exposure_rank",
        "duplicate_position_groups",
        "largest_position",
    }

    assert [row["search_term"] for row in data["fund_matches"]] == FUND_SEARCH_TERMS
    assert [row["search_term"] for row in data["issuer_matches"]] == ISSUER_SEARCH_TERMS

    summary = data["selected_position_summary"]
    assert summary["matched_fund_count"] == len(FUND_SEARCH_TERMS)
    assert summary["matched_issuer_count"] == len(ISSUER_SEARCH_TERMS)

    ranking = data["manager_exposure_rank"]
    assert [row["rank"] for row in ranking] == list(range(1, len(ranking) + 1))
    assert [row["total_value_usd"] for row in ranking] == sorted(
        [row["total_value_usd"] for row in ranking],
        reverse=True,
    )
    for row in ranking:
        assert row["matched_cusips"] == sorted(row["matched_cusips"])

    duplicates = data["duplicate_position_groups"]
    assert duplicates == sorted(
        duplicates,
        key=lambda row: (row["accession_number"], row["cusip"]),
    )
    for row in duplicates:
        assert row["position_ids"] == sorted(row["position_ids"])
        assert row["duplicate_count"] == len(row["position_ids"])
        assert row["duplicate_count"] > 1
