import csv
import re
from pathlib import Path


OUTPUT = Path("/root/transfer2_site_hop_memo.md")
REQUEST = Path("/root/data/transfer2_site_hops.tsv")
DISTANCE_DATA = Path("/root/data/googleDistanceMatrix/distance.csv")


def parse_minutes(duration_text: str) -> int:
    total = 0
    hour_match = re.search(r"(\d+)\s*hour", duration_text)
    minute_match = re.search(r"(\d+)\s*min", duration_text)
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if minute_match:
        total += int(minute_match.group(1))
    return total


def load_distances():
    table = {}
    with DISTANCE_DATA.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[(row["origin"].strip(), row["destination"].strip())] = row
    return table


def expected_markdown() -> str:
    table = load_distances()
    feasible = []
    infeasible = []
    with REQUEST.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            duration_minutes = parse_minutes(table[(row["origin"], row["destination"])]["duration"])
            margin = int(row["max_duration_minutes"]) - duration_minutes
            entry = {
                "lane_id": row["lane_id"],
                "origin": row["origin"],
                "destination": row["destination"],
                "duration_minutes": duration_minutes,
                "margin": margin,
            }
            if margin >= 0:
                feasible.append(entry)
            else:
                infeasible.append(entry)

    feasible.sort(key=lambda item: (-item["margin"], item["lane_id"]))
    infeasible.sort(key=lambda item: (abs(item["margin"]), item["lane_id"]))

    lines = ["# Southeast Site-Hop Feasibility", "", "## Feasible"]
    for item in feasible:
        lines.append(
            f"- {item['lane_id']} | {item['origin']} -> {item['destination']} | "
            f"{item['duration_minutes']} min | margin +{item['margin']}"
        )
    lines.extend(["", "## Infeasible"])
    for item in infeasible:
        lines.append(
            f"- {item['lane_id']} | {item['origin']} -> {item['destination']} | "
            f"{item['duration_minutes']} min | margin {item['margin']}"
        )
    lines.extend(
        [
            "",
            f"feasible_count: {len(feasible)}",
            f"infeasible_count: {len(infeasible)}",
            "tool_called: search_driving_distance",
            "",
        ]
    )
    return "\n".join(lines)


def test_output_exists():
    assert OUTPUT.exists(), "missing site-hop memo"


def test_markdown_matches_expected():
    actual = OUTPUT.read_text(encoding="utf-8")
    assert actual == expected_markdown()
