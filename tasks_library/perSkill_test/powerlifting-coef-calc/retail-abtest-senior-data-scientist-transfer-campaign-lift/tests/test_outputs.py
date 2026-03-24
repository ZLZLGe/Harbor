import math

import pandas as pd

OUTPUT_FILE = "/root/data/campaign_lift_analysis.xlsx"
GROUP_ORDER = ["Control", "Bundle", "Discount", "Loyalty"]
EXPECTED_COLUMNS = [
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


def build_expected() -> pd.DataFrame:
    exposure = pd.read_excel(OUTPUT_FILE, sheet_name="ExposureSummary")
    orders = pd.read_excel(OUTPUT_FILE, sheet_name="Orders")

    exposure_grouped = (
        exposure.groupby("CampaignGroup", as_index=False)
        .agg(
            StoreCount=("StoreID", "nunique"),
            TotalVisitors=("Visitors", "sum"),
            TotalPurchasers=("Purchasers", "sum"),
        )
    )
    order_grouped = (
        orders.groupby("CampaignGroup")
        .agg(
            TotalRevenue=("Revenue", "sum"),
            AverageOrderRevenue=("Revenue", "mean"),
            OrderRevenueStd=("Revenue", lambda s: s.std(ddof=1)),
            OrderCount=("Revenue", "count"),
        )
        .reset_index()
    )

    expected = exposure_grouped.merge(order_grouped, on="CampaignGroup", how="inner")
    expected["ConversionRate"] = expected["TotalPurchasers"] / expected["TotalVisitors"]
    expected["ConversionRateSE"] = (
        expected["ConversionRate"] * (1 - expected["ConversionRate"]) / expected["TotalVisitors"]
    ) ** 0.5
    expected["AverageOrderRevenueSE"] = expected["OrderRevenueStd"] / expected["OrderCount"] ** 0.5

    expected = expected.set_index("CampaignGroup").loc[GROUP_ORDER].reset_index()
    control = expected.loc[expected["CampaignGroup"] == "Control"].iloc[0]

    expected["AbsLiftVsControl_ConversionRate"] = expected["ConversionRate"] - control["ConversionRate"]
    expected["RelLiftVsControl_ConversionRatePct"] = (
        expected["ConversionRate"] / control["ConversionRate"] - 1
    ) * 100
    expected["ConversionRateLiftSE"] = (
        expected["ConversionRateSE"] ** 2 + control["ConversionRateSE"] ** 2
    ) ** 0.5
    expected["ConversionRateLiftCI95Low"] = (
        expected["AbsLiftVsControl_ConversionRate"] - 1.96 * expected["ConversionRateLiftSE"]
    )
    expected["ConversionRateLiftCI95High"] = (
        expected["AbsLiftVsControl_ConversionRate"] + 1.96 * expected["ConversionRateLiftSE"]
    )

    expected["AbsLiftVsControl_AOV"] = expected["AverageOrderRevenue"] - control["AverageOrderRevenue"]
    expected["RelLiftVsControl_AOVPct"] = (
        expected["AverageOrderRevenue"] / control["AverageOrderRevenue"] - 1
    ) * 100
    expected["AOVLiftSE"] = (
        expected["AverageOrderRevenueSE"] ** 2 + control["AverageOrderRevenueSE"] ** 2
    ) ** 0.5
    expected["AOVLiftCI95Low"] = expected["AbsLiftVsControl_AOV"] - 1.96 * expected["AOVLiftSE"]
    expected["AOVLiftCI95High"] = expected["AbsLiftVsControl_AOV"] + 1.96 * expected["AOVLiftSE"]

    expected["Decision"] = expected.apply(
        lambda row: "Control"
        if row["CampaignGroup"] == "Control"
        else "Significant Winner"
        if row["ConversionRateLiftCI95Low"] > 0 and row["AOVLiftCI95Low"] > 0
        else "No Clear Win",
        axis=1,
    )

    expected["TotalRevenue"] = expected["TotalRevenue"].round(2)
    for column in [
        "ConversionRate",
        "ConversionRateSE",
        "AbsLiftVsControl_ConversionRate",
        "ConversionRateLiftSE",
        "ConversionRateLiftCI95Low",
        "ConversionRateLiftCI95High",
    ]:
        expected[column] = expected[column].round(6)

    for column in [
        "AverageOrderRevenue",
        "AverageOrderRevenueSE",
        "AbsLiftVsControl_AOV",
        "AOVLiftSE",
        "AOVLiftCI95Low",
        "AOVLiftCI95High",
    ]:
        expected[column] = expected[column].round(4)

    for column in [
        "RelLiftVsControl_ConversionRatePct",
        "RelLiftVsControl_AOVPct",
    ]:
        expected[column] = expected[column].round(2)

    expected.loc[expected["CampaignGroup"] == "Control", [
        "AbsLiftVsControl_ConversionRate",
        "RelLiftVsControl_ConversionRatePct",
        "AbsLiftVsControl_AOV",
        "RelLiftVsControl_AOVPct",
    ]] = 0

    return expected[EXPECTED_COLUMNS]


def test_workbook_has_required_sheets():
    workbook = pd.ExcelFile(OUTPUT_FILE)
    assert workbook.sheet_names == ["ExposureSummary", "Orders", "Analysis"]


def test_analysis_sheet_has_expected_columns():
    analysis = pd.read_excel(OUTPUT_FILE, sheet_name="Analysis")
    assert analysis.columns.tolist() == EXPECTED_COLUMNS


def test_analysis_row_order_and_row_count():
    analysis = pd.read_excel(OUTPUT_FILE, sheet_name="Analysis")
    assert len(analysis) == 4
    assert analysis["CampaignGroup"].tolist() == GROUP_ORDER


def test_analysis_matches_expected_values():
    analysis = pd.read_excel(OUTPUT_FILE, sheet_name="Analysis")
    expected = build_expected()

    for column in EXPECTED_COLUMNS:
        if pd.api.types.is_numeric_dtype(expected[column]):
            for actual, target in zip(analysis[column], expected[column], strict=True):
                assert math.isclose(actual, target, abs_tol=1e-6), (
                    f"Column {column} mismatch: actual={actual}, expected={target}"
                )
        else:
            assert analysis[column].tolist() == expected[column].tolist()


def test_control_row_uses_control_conventions():
    analysis = pd.read_excel(OUTPUT_FILE, sheet_name="Analysis")
    control = analysis.loc[analysis["CampaignGroup"] == "Control"].iloc[0]
    assert control["AbsLiftVsControl_ConversionRate"] == 0
    assert control["RelLiftVsControl_ConversionRatePct"] == 0
    assert control["AbsLiftVsControl_AOV"] == 0
    assert control["RelLiftVsControl_AOVPct"] == 0
    assert control["ConversionRateLiftSE"] > 0
    assert control["AOVLiftSE"] > 0
    assert control["Decision"] == "Control"


def test_significance_decision_identifies_single_winner():
    analysis = pd.read_excel(OUTPUT_FILE, sheet_name="Analysis")
    winners = analysis.loc[analysis["Decision"] == "Significant Winner", "CampaignGroup"].tolist()
    assert winners == ["Bundle"]
    discount = analysis.loc[analysis["CampaignGroup"] == "Discount"].iloc[0]
    assert discount["ConversionRateLiftCI95Low"] > 0
    assert discount["AOVLiftCI95Low"] < 0
