#!/bin/bash
set -euo pipefail

cat <<'PY' > /tmp/solve_similar.py
import json
import pdfplumber


PDF_PATH = "/root/demographic_brief.pdf"
OUTPUT_PATH = "/root/similar_demographic_summary.json"
QUARTILES = ["Q1", "Q2", "Q3", "Q4"]


def parse_int(value):
    return int(str(value).replace(",", "").strip())


def load_rows():
    rows = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for raw_row in table:
                    if not raw_row or len(raw_row) < 6:
                        continue
                    first_cell = str(raw_row[0]).strip()
                    if not first_cell.isdigit():
                        continue
                    rows.append(
                        {
                            "sa2_code": parse_int(raw_row[0]),
                            "sa2_name": str(raw_row[1]).strip(),
                            "state": str(raw_row[2]).strip(),
                            "population_2024": parse_int(raw_row[3]),
                            "earners": parse_int(raw_row[4]),
                            "median_income": parse_int(raw_row[5]),
                        }
                    )
    if not rows:
        raise RuntimeError("No demographic rows were extracted from the PDF")
    rows.sort(key=lambda item: item["sa2_code"])
    ranked = sorted(rows, key=lambda item: (item["median_income"], item["sa2_code"]))
    total_rows = len(ranked)
    for index, row in enumerate(ranked):
        quartile_index = min((index * 4) // total_rows, 3)
        row["quartile"] = QUARTILES[quartile_index]
        row["total"] = row["earners"] * row["median_income"]
    by_code = {row["sa2_code"]: row for row in ranked}
    return [by_code[row["sa2_code"]] for row in rows]


def build_output(rows):
    states = sorted({row["state"] for row in rows})
    population_totals = {state: 0 for state in states}
    earner_totals = {state: 0 for state in states}
    region_counts = {state: 0 for state in states}
    quartile_earners = {(state, quartile): 0 for state in states for quartile in QUARTILES}

    for row in rows:
        state = row["state"]
        population_totals[state] += row["population_2024"]
        earner_totals[state] += row["earners"]
        region_counts[state] += 1
        quartile_earners[(state, row["quartile"])] += row["earners"]

    top_regions = sorted(rows, key=lambda row: (-row["total"], row["sa2_code"]))[:3]
    return {
        "state_population_totals": [{"state": state, "population_2024": population_totals[state]} for state in states],
        "state_earner_totals": [{"state": state, "earners": earner_totals[state]} for state in states],
        "state_region_counts": [{"state": state, "region_count": region_counts[state]} for state in states],
        "state_income_quartile_earners": [
            {"state": state, "quartile": quartile, "earners": quartile_earners[(state, quartile)]}
            for state in states
            for quartile in QUARTILES
        ],
        "top_total_regions": [
            {
                "sa2_code": row["sa2_code"],
                "sa2_name": row["sa2_name"],
                "state": row["state"],
                "total": row["total"],
            }
            for row in top_regions
        ],
    }


def main():
    rows = load_rows()
    result = build_output(rows)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
PY

python3 /tmp/solve_similar.py
