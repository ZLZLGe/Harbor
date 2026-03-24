#!/bin/bash

set -e

WORK_DIR=/root/solve
INPUT_FILE=/root/data/meet_results.xlsx
OUTPUT_FILE=/root/data/wilks_scoreboard.xlsx

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

uv init --python 3.12
uv add openpyxl==3.1.5
uv add typer==0.21.1

cat > solve_wilks.py <<'PY'
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties


REQUIRED_HEADERS = {
    "Name",
    "Sex",
    "BodyweightKg",
    "Best3SquatKg",
    "Best3BenchKg",
    "Best3DeadliftKg",
}


def calculate_wilks(sex: str, bodyweight: float, total: float) -> float:
    if sex == "M":
        x = max(40.0, min(201.9, bodyweight))
        a, b, c, d, e, f = (
            -216.0475144,
            16.2606339,
            -0.002388645,
            -0.00113732,
            7.01863e-06,
            -1.291e-08,
        )
    else:
        x = max(26.51, min(154.53, bodyweight))
        a, b, c, d, e, f = (
            594.31747775582,
            -27.23842536447,
            0.82112226871,
            -0.00930733913,
            4.731582e-05,
            -9.054e-08,
        )

    coefficient = 500 / (a + b * x + c * x**2 + d * x**3 + e * x**4 + f * x**5)
    return round(total * coefficient, 3)


def build_wilks_formula(sex_ref: str, bodyweight_ref: str, total_ref: str) -> str:
    male_bw = f"MAX(40,MIN(201.9,{bodyweight_ref}))"
    female_bw = f"MAX(26.51,MIN(154.53,{bodyweight_ref}))"

    male_poly = (
        f"(-216.0475144+16.2606339*{male_bw}"
        f"-0.002388645*POWER({male_bw},2)"
        f"-0.00113732*POWER({male_bw},3)"
        f"+7.01863E-06*POWER({male_bw},4)"
        f"-1.291E-08*POWER({male_bw},5))"
    )
    female_poly = (
        f"(594.31747775582-27.23842536447*{female_bw}"
        f"+0.82112226871*POWER({female_bw},2)"
        f"-0.00930733913*POWER({female_bw},3)"
        f"+4.731582E-05*POWER({female_bw},4)"
        f"-9.054E-08*POWER({female_bw},5))"
    )

    return f'=ROUND(IF({sex_ref}="M",{total_ref}*(500/{male_poly}),{total_ref}*(500/{female_poly})),3)'


def main(
    input_file: str = "/root/data/meet_results.xlsx",
    output_file: str = "/root/data/wilks_scoreboard.xlsx",
) -> None:
    workbook = load_workbook(input_file)
    source_sheet = workbook["Meet Results"]
    target_sheet = workbook["Wilks"]

    headers = [cell.value for cell in source_sheet[1]]
    selected_headers = [header for header in headers if header in REQUIRED_HEADERS]
    header_index = {header: idx + 1 for idx, header in enumerate(headers)}

    records = []
    for row in source_sheet.iter_rows(min_row=2, values_only=True):
        values = {header: row[index - 1] for header, index in header_index.items()}
        total = round(
            float(values["Best3SquatKg"])
            + float(values["Best3BenchKg"])
            + float(values["Best3DeadliftKg"]),
            3,
        )
        score = calculate_wilks(values["Sex"], float(values["BodyweightKg"]), total)
        records.append((score, values))

    records.sort(key=lambda item: item[0], reverse=True)

    output_headers = selected_headers + ["TotalKg", "Wilks"]
    for col_idx, header in enumerate(output_headers, start=1):
        cell = target_sheet.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)

    output_column_refs = {
        header: get_column_letter(col_idx) for col_idx, header in enumerate(selected_headers, start=1)
    }
    total_col = get_column_letter(len(selected_headers) + 1)
    wilks_col = get_column_letter(len(selected_headers) + 2)

    for row_idx, (_, record) in enumerate(records, start=2):
        for col_idx, header in enumerate(selected_headers, start=1):
            target_sheet.cell(row=row_idx, column=col_idx, value=record[header])

        total_formula = (
            f'=ROUND({output_column_refs["Best3SquatKg"]}{row_idx}'
            f'+{output_column_refs["Best3BenchKg"]}{row_idx}'
            f'+{output_column_refs["Best3DeadliftKg"]}{row_idx},3)'
        )
        wilks_formula = build_wilks_formula(
            f'{output_column_refs["Sex"]}{row_idx}',
            f'{output_column_refs["BodyweightKg"]}{row_idx}',
            f"{total_col}{row_idx}",
        )

        total_cell = target_sheet.cell(row=row_idx, column=len(selected_headers) + 1, value=total_formula)
        wilks_cell = target_sheet.cell(row=row_idx, column=len(selected_headers) + 2, value=wilks_formula)
        total_cell.number_format = "0.000"
        wilks_cell.number_format = "0.000"

    target_sheet.freeze_panes = "A2"
    target_sheet.auto_filter.ref = f"A1:{wilks_col}{len(records) + 1}"

    workbook.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True, forceFullCalc=True)
    workbook.save(output_file)


if __name__ == "__main__":
    import typer

    typer.run(main)
PY

uv run solve_wilks.py --input-file "$INPUT_FILE" --output-file "$OUTPUT_FILE"
