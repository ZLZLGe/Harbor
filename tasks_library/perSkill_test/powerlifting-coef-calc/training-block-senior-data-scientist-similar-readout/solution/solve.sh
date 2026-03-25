#!/bin/bash
set -euo pipefail

mkdir -p /root/results

python3 - <<'PY'
from math import sqrt
from statistics import mean, stdev
from openpyxl import Workbook, load_workbook

INPUT_FILE = "/root/data/training_block_experiment.xlsx"
OUTPUT_FILE = "/root/results/training_block_readout.xlsx"


def load_sheet_rows(sheet):
    rows = list(sheet.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]


def total_kg(row):
    return row["squat_kg"] + row["bench_kg"] + row["deadlift_kg"]


def build_summary(rows, metric):
    treatment = [row[metric] for row in rows if row["training_group"] == "treatment"]
    control = [row[metric] for row in rows if row["training_group"] == "control"]

    treatment_mean = mean(treatment)
    control_mean = mean(control)
    mean_diff = treatment_mean - control_mean

    treatment_sd = stdev(treatment)
    control_sd = stdev(control)
    n_treatment = len(treatment)
    n_control = len(control)

    se = sqrt((treatment_sd ** 2) / n_treatment + (control_sd ** 2) / n_control)
    ci95_lower = mean_diff - 1.96 * se
    ci95_upper = mean_diff + 1.96 * se

    pooled_sd = sqrt(
        (
            (n_treatment - 1) * (treatment_sd ** 2)
            + (n_control - 1) * (control_sd ** 2)
        )
        / (n_treatment + n_control - 2)
    )
    cohens_d = mean_diff / pooled_sd

    return [
        metric,
        treatment_mean,
        control_mean,
        mean_diff,
        ci95_lower,
        ci95_upper,
        cohens_d,
        n_treatment,
        n_control,
        abs(n_treatment - n_control) <= 1,
    ]


source_wb = load_workbook(INPUT_FILE, data_only=True)
roster_rows = load_sheet_rows(source_wb["Roster"])
baseline_rows = {
    row["athlete_id"]: row for row in load_sheet_rows(source_wb["BaselineTest"])
}
end_rows = {
    row["athlete_id"]: row for row in load_sheet_rows(source_wb["BlockEnd"])
}

athlete_rows = []
for roster in sorted(roster_rows, key=lambda item: item["athlete_id"]):
    athlete_id = roster["athlete_id"]
    baseline = baseline_rows[athlete_id]
    endline = end_rows[athlete_id]

    baseline_total = total_kg(baseline)
    end_total = total_kg(endline)
    delta_total = end_total - baseline_total

    athlete_rows.append(
        [
            athlete_id,
            roster["athlete_name"],
            roster["sex"],
            roster["training_group"],
            roster["cohort"],
            baseline["bodyweight_kg"],
            baseline_total,
            endline["bodyweight_kg"],
            end_total,
            delta_total,
            delta_total / baseline["bodyweight_kg"],
        ]
    )

summary_input_rows = [
    {
        "training_group": row[3],
        "delta_total_kg": row[9],
        "delta_total_per_bw": row[10],
    }
    for row in athlete_rows
]

output_wb = Workbook()
athlete_ws = output_wb.active
athlete_ws.title = "AthleteReadout"
summary_ws = output_wb.create_sheet("Summary")

athlete_headers = [
    "athlete_id",
    "athlete_name",
    "sex",
    "training_group",
    "cohort",
    "baseline_bodyweight_kg",
    "baseline_total_kg",
    "end_bodyweight_kg",
    "end_total_kg",
    "delta_total_kg",
    "delta_total_per_bw",
]
athlete_ws.append(athlete_headers)
for row in athlete_rows:
    athlete_ws.append(row)

summary_headers = [
    "metric",
    "treatment_mean",
    "control_mean",
    "mean_diff",
    "ci95_lower",
    "ci95_upper",
    "cohens_d",
    "n_treatment",
    "n_control",
    "sample_size_balanced",
]
summary_ws.append(summary_headers)
summary_ws.append(build_summary(summary_input_rows, "delta_total_kg"))
summary_ws.append(build_summary(summary_input_rows, "delta_total_per_bw"))

output_wb.save(OUTPUT_FILE)
PY
