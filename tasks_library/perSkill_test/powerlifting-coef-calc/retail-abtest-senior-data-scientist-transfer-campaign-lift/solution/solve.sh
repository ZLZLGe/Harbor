#!/bin/bash

set -euo pipefail

WORK_DIR=/root/solve
INPUT_FILE=/root/data/campaign_lift_analysis.xlsx

mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

uv init --python 3.12
uv add pandas==2.2.3 openpyxl==3.1.5 numpy==2.1.1

cat > "${WORK_DIR}/solve_campaign.py" <<'PY'
import math

import openpyxl
import pandas as pd


INPUT_FILE = "/root/data/campaign_lift_analysis.xlsx"
GROUP_ORDER = ["Control", "Bundle", "Discount", "Loyalty"]
OUTPUT_COLUMNS = [
    "CampaignGroup",
    "StoreCount",
    "TotalVisitors",
    "TotalPurchasers",
    "TotalRevenue",
    "ConversionRate",
    "ConversionRateSE",
    "AverageOrderRevenue",
    "AverageOrderRevenueSE",
    "AbsLiftVsControl_ConversionRate",
    "RelLiftVsControl_ConversionRatePct",
    "ConversionRateLiftSE",
    "ConversionRateLiftCI95Low",
    "ConversionRateLiftCI95High",
    "AbsLiftVsControl_AOV",
    "RelLiftVsControl_AOVPct",
    "AOVLiftSE",
    "AOVLiftCI95Low",
    "AOVLiftCI95High",
    "Decision",
]


def build_analysis() -> pd.DataFrame:
    exposure = pd.read_excel(INPUT_FILE, sheet_name="ExposureSummary")
    orders = pd.read_excel(INPUT_FILE, sheet_name="Orders")

    exposure_grouped = (
        exposure.groupby("CampaignGroup", as_index=False)
        .agg(
            StoreCount=("StoreID", "nunique"),
            TotalVisitors=("Visitors", "sum"),
            TotalPurchasers=("Purchasers", "sum"),
        )
    )
    revenue_grouped = (
        orders.groupby("CampaignGroup")
        .agg(
            TotalRevenue=("Revenue", "sum"),
            AverageOrderRevenue=("Revenue", "mean"),
            OrderRevenueStd=("Revenue", lambda s: s.std(ddof=1)),
            OrderCount=("Revenue", "count"),
        )
        .reset_index()
    )

    analysis = exposure_grouped.merge(revenue_grouped, on="CampaignGroup", how="inner")
    analysis["ConversionRate"] = analysis["TotalPurchasers"] / analysis["TotalVisitors"]
    analysis["ConversionRateSE"] = (
        analysis["ConversionRate"] * (1 - analysis["ConversionRate"]) / analysis["TotalVisitors"]
    ) ** 0.5
    analysis["AverageOrderRevenueSE"] = analysis["OrderRevenueStd"] / analysis["OrderCount"] ** 0.5

    analysis = analysis.set_index("CampaignGroup").loc[GROUP_ORDER].reset_index()
    control = analysis.loc[analysis["CampaignGroup"] == "Control"].iloc[0]

    analysis["AbsLiftVsControl_ConversionRate"] = analysis["ConversionRate"] - control["ConversionRate"]
    analysis["RelLiftVsControl_ConversionRatePct"] = (
        analysis["ConversionRate"] / control["ConversionRate"] - 1
    ) * 100
    analysis["ConversionRateLiftSE"] = (
        analysis["ConversionRateSE"] ** 2 + control["ConversionRateSE"] ** 2
    ) ** 0.5
    analysis["ConversionRateLiftCI95Low"] = (
        analysis["AbsLiftVsControl_ConversionRate"] - 1.96 * analysis["ConversionRateLiftSE"]
    )
    analysis["ConversionRateLiftCI95High"] = (
        analysis["AbsLiftVsControl_ConversionRate"] + 1.96 * analysis["ConversionRateLiftSE"]
    )

    analysis["AbsLiftVsControl_AOV"] = analysis["AverageOrderRevenue"] - control["AverageOrderRevenue"]
    analysis["RelLiftVsControl_AOVPct"] = (
        analysis["AverageOrderRevenue"] / control["AverageOrderRevenue"] - 1
    ) * 100
    analysis["AOVLiftSE"] = (
        analysis["AverageOrderRevenueSE"] ** 2 + control["AverageOrderRevenueSE"] ** 2
    ) ** 0.5
    analysis["AOVLiftCI95Low"] = analysis["AbsLiftVsControl_AOV"] - 1.96 * analysis["AOVLiftSE"]
    analysis["AOVLiftCI95High"] = analysis["AbsLiftVsControl_AOV"] + 1.96 * analysis["AOVLiftSE"]

    analysis["Decision"] = analysis.apply(
        lambda row: "Control"
        if row["CampaignGroup"] == "Control"
        else "Significant Winner"
        if row["ConversionRateLiftCI95Low"] > 0 and row["AOVLiftCI95Low"] > 0
        else "No Clear Win",
        axis=1,
    )

    analysis["TotalRevenue"] = analysis["TotalRevenue"].round(2)
    for column in [
        "ConversionRate",
        "ConversionRateSE",
        "AbsLiftVsControl_ConversionRate",
        "ConversionRateLiftSE",
        "ConversionRateLiftCI95Low",
        "ConversionRateLiftCI95High",
    ]:
        analysis[column] = analysis[column].round(6)

    for column in [
        "AverageOrderRevenue",
        "AverageOrderRevenueSE",
        "AbsLiftVsControl_AOV",
        "AOVLiftSE",
        "AOVLiftCI95Low",
        "AOVLiftCI95High",
    ]:
        analysis[column] = analysis[column].round(4)

    for column in [
        "RelLiftVsControl_ConversionRatePct",
        "RelLiftVsControl_AOVPct",
    ]:
        analysis[column] = analysis[column].round(2)

    analysis.loc[analysis["CampaignGroup"] == "Control", [
        "AbsLiftVsControl_ConversionRate",
        "RelLiftVsControl_ConversionRatePct",
        "AbsLiftVsControl_AOV",
        "RelLiftVsControl_AOVPct",
    ]] = 0

    return analysis[OUTPUT_COLUMNS]


def write_analysis(df: pd.DataFrame) -> None:
    workbook = openpyxl.load_workbook(INPUT_FILE)
    sheet = workbook["Analysis"]

    for row in sheet.iter_rows():
        for cell in row:
            cell.value = None

    for col_idx, column in enumerate(df.columns, start=1):
        sheet.cell(row=1, column=col_idx, value=column)

    for row_idx, (_, row) in enumerate(df.iterrows(), start=2):
        for col_idx, column in enumerate(df.columns, start=1):
            value = row[column]
            if pd.isna(value):
                value = None
            elif isinstance(value, (pd.Timestamp,)):
                value = value.to_pydatetime()
            elif hasattr(value, "item"):
                value = value.item()
            sheet.cell(row=row_idx, column=col_idx, value=value)

    workbook.save(INPUT_FILE)


if __name__ == "__main__":
    write_analysis(build_analysis())
PY

uv run "${WORK_DIR}/solve_campaign.py"
