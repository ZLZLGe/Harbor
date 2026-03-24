#!/bin/bash

set -euo pipefail

INPUT_FILE="${INPUT_FILE:-/root/data/bench_nationals_results.csv}"
OUTPUT_FILE="${OUTPUT_FILE:-/root/data/bench_goodlift_ranking.csv}"

python3 - "$INPUT_FILE" "$OUTPUT_FILE" <<'PY'
import csv
import math
import sys
from collections import defaultdict

input_file = sys.argv[1]
output_file = sys.argv[2]

OUTPUT_HEADERS = [
    "OverallRank",
    "ClassRank",
    "ScoringClass",
    "LifterName",
    "Province",
    "Sex",
    "Equipment",
    "Event",
    "BodyweightKg",
    "Best3BenchKg",
    "Goodlift",
]

PARAMETERS = {
    ("B", "M", "Raw"): (320.98041, 281.40258, 0.01008),
    ("B", "M", "Single-ply"): (381.22073, 733.79378, 0.02398),
    ("B", "F", "Raw"): (142.40398, 442.52671, 0.04724),
    ("B", "F", "Single-ply"): (221.82209, 357.00377, 0.02937),
}


def calculate_goodlift(sex: str, equipment: str, event: str, bodyweight: float, total: float) -> float:
    if bodyweight < 35.0 or total == 0.0:
        return 0.0

    sex_key = "F" if sex == "F" else "M"
    a, b, c = PARAMETERS[(event, sex_key, equipment)]
    denominator = a - b * math.exp(-c * bodyweight)
    return round(total * max(0.0, 100.0 / denominator), 2)


with open(input_file, newline="", encoding="utf-8") as handle:
    records = list(csv.DictReader(handle))

for row in records:
    bodyweight = float(row["BodyweightKg"])
    bench = float(row["Best3BenchKg"])
    row["ScoringClass"] = f'{row["Sex"]}|{row["Equipment"]}|{row["Event"]}'
    row["GoodliftValue"] = calculate_goodlift(
        row["Sex"],
        row["Equipment"],
        row["Event"],
        bodyweight,
        bench,
    )


def sort_key(row):
    return (-row["GoodliftValue"], -float(row["Best3BenchKg"]), row["LifterName"])


class_groups = defaultdict(list)
for row in records:
    class_groups[row["ScoringClass"]].append(row)

for items in class_groups.values():
    items.sort(key=sort_key)
    for rank, row in enumerate(items, start=1):
        row["ClassRank"] = str(rank)

records.sort(key=sort_key)
for rank, row in enumerate(records, start=1):
    row["OverallRank"] = str(rank)

with open(output_file, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS)
    writer.writeheader()
    for row in records:
        writer.writerow(
            {
                "OverallRank": row["OverallRank"],
                "ClassRank": row["ClassRank"],
                "ScoringClass": row["ScoringClass"],
                "LifterName": row["LifterName"],
                "Province": row["Province"],
                "Sex": row["Sex"],
                "Equipment": row["Equipment"],
                "Event": row["Event"],
                "BodyweightKg": row["BodyweightKg"],
                "Best3BenchKg": row["Best3BenchKg"],
                "Goodlift": f'{row["GoodliftValue"]:.2f}',
            }
        )
PY
