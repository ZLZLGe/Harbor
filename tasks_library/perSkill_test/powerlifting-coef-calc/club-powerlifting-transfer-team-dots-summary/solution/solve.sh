#!/bin/bash

set -e

WORK_DIR=/root/solve
INPUT_FILE=/root/data/club_cup_entries.xlsx
OUTPUT_FILE=/root/data/team_dots_summary.xlsx

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

uv init --python 3.12
uv add openpyxl==3.1.5
uv add typer==0.21.1

cat > solve_team_dots.py <<'PY'
from collections import defaultdict

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties


REQUIRED_HEADERS = [
    "Club",
    "LifterName",
    "Sex",
    "BodyweightKg",
    "Best3SquatKg",
    "Best3BenchKg",
    "Best3DeadliftKg",
]

MALE_COEFFICIENTS = (-0.0000010930, 0.0007391293, -0.1918759221, 24.0900756, -307.75076)
FEMALE_COEFFICIENTS = (-0.0000010706, 0.0005158568, -0.1126655495, 13.6175032, -57.96288)


def calculate_dots(sex: str, bodyweight: float, total: float) -> float:
    if sex == "M":
        adjusted = max(40.0, min(210.0, bodyweight))
        a, b, c, d, e = MALE_COEFFICIENTS
    else:
        adjusted = max(40.0, min(150.0, bodyweight))
        a, b, c, d, e = FEMALE_COEFFICIENTS

    denominator = (
        a * adjusted**4
        + b * adjusted**3
        + c * adjusted**2
        + d * adjusted
        + e
    )
    return round(total * (500 / denominator), 3)


def build_dots_formula(sex_ref: str, bodyweight_ref: str, total_ref: str) -> str:
    male_bw = f"MAX(40,MIN(210,{bodyweight_ref}))"
    female_bw = f"MAX(40,MIN(150,{bodyweight_ref}))"

    male_poly = (
        f"(-0.0000010930*POWER({male_bw},4)"
        f"+0.0007391293*POWER({male_bw},3)"
        f"-0.1918759221*POWER({male_bw},2)"
        f"+24.0900756*{male_bw}"
        f"-307.75076)"
    )
    female_poly = (
        f"(-0.0000010706*POWER({female_bw},4)"
        f"+0.0005158568*POWER({female_bw},3)"
        f"-0.1126655495*POWER({female_bw},2)"
        f"+13.6175032*{female_bw}"
        f"-57.96288)"
    )

    return (
        f'=ROUND(IF({sex_ref}="M",{total_ref}*(500/{male_poly}),'
        f'{total_ref}*(500/{female_poly})),3)'
    )


def main(
    input_file: str = "/root/data/club_cup_entries.xlsx",
    output_file: str = "/root/data/team_dots_summary.xlsx",
) -> None:
    workbook = load_workbook(input_file)
    entries_sheet = workbook["Club Entries"]
    team_sheet = workbook["Team Podium"]
    athlete_sheet = workbook.create_sheet("Athlete Dots", 1)

    source_headers = [cell.value for cell in entries_sheet[1]]
    selected_headers = [header for header in source_headers if header in REQUIRED_HEADERS]
    header_index = {header: idx + 1 for idx, header in enumerate(source_headers)}

    records = []
    for row in entries_sheet.iter_rows(min_row=2, values_only=True):
        values = {header: row[index - 1] for header, index in header_index.items()}
        total = round(
            float(values["Best3SquatKg"])
            + float(values["Best3BenchKg"])
            + float(values["Best3DeadliftKg"]),
            3,
        )
        dots = calculate_dots(values["Sex"], float(values["BodyweightKg"]), total)
        record = {header: values[header] for header in selected_headers}
        record["TotalKg"] = total
        record["DotsScore"] = dots
        records.append(record)

    records.sort(key=lambda item: item["DotsScore"], reverse=True)

    output_headers = selected_headers + ["TotalKg", "Dots"]
    for col_idx, header in enumerate(output_headers, start=1):
        cell = athlete_sheet.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    col_refs = {header: get_column_letter(idx) for idx, header in enumerate(selected_headers, start=1)}
    total_col = get_column_letter(len(selected_headers) + 1)
    dots_col = get_column_letter(len(selected_headers) + 2)

    for row_idx, record in enumerate(records, start=2):
        for col_idx, header in enumerate(selected_headers, start=1):
            athlete_sheet.cell(row=row_idx, column=col_idx, value=record[header])

        total_formula = (
            f'=ROUND({col_refs["Best3SquatKg"]}{row_idx}'
            f'+{col_refs["Best3BenchKg"]}{row_idx}'
            f'+{col_refs["Best3DeadliftKg"]}{row_idx},3)'
        )
        dots_formula = build_dots_formula(
            f'{col_refs["Sex"]}{row_idx}',
            f'{col_refs["BodyweightKg"]}{row_idx}',
            f"{total_col}{row_idx}",
        )

        total_cell = athlete_sheet.cell(row=row_idx, column=len(selected_headers) + 1, value=total_formula)
        dots_cell = athlete_sheet.cell(row=row_idx, column=len(selected_headers) + 2, value=dots_formula)
        total_cell.number_format = "0.000"
        dots_cell.number_format = "0.000"

    athlete_sheet.freeze_panes = "A2"
    athlete_sheet.auto_filter.ref = f"A1:{dots_col}{len(records) + 1}"

    team_headers = ["Rank", "Club", "ScoringLifters", "TeamDots"]
    for col_idx, header in enumerate(team_headers, start=1):
        cell = team_sheet.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    club_records = defaultdict(list)
    for record in records:
        club_records[record["Club"]].append(record)

    team_rows = []
    for club, club_entries in club_records.items():
        top_three = sorted(club_entries, key=lambda item: item["DotsScore"], reverse=True)[:3]
        scoring_lifters = ", ".join(item["LifterName"] for item in top_three)
        team_total = round(sum(item["DotsScore"] for item in top_three), 3)
        team_rows.append((club, scoring_lifters, team_total))

    team_rows.sort(key=lambda item: item[2], reverse=True)

    for row_idx, (club, scoring_lifters, team_total) in enumerate(team_rows, start=2):
        team_sheet.cell(row=row_idx, column=1, value=row_idx - 1)
        team_sheet.cell(row=row_idx, column=2, value=club)
        team_sheet.cell(row=row_idx, column=3, value=scoring_lifters)
        total_cell = team_sheet.cell(row=row_idx, column=4, value=team_total)
        total_cell.number_format = "0.000"

    team_sheet.freeze_panes = "A2"
    team_sheet.auto_filter.ref = f"A1:D{len(team_rows) + 1}"

    workbook.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True, forceFullCalc=True)
    workbook.save(output_file)


if __name__ == "__main__":
    import typer

    typer.run(main)
PY

uv run solve_team_dots.py --input-file "$INPUT_FILE" --output-file "$OUTPUT_FILE"
