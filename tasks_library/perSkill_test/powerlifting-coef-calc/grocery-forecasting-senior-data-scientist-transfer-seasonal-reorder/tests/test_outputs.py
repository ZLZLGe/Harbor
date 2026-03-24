from math import ceil

import pandas as pd
from pandas.testing import assert_frame_equal


OUTPUT_FILE = "/root/data/store_reorder_forecast.xlsx"
TRAIN_DAYS = 28
HOLDOUT_DAYS = 7
FORECAST_DAYS = 14

FORECAST_COLUMNS = [
    "StoreID",
    "SKU",
    "Category",
    "ForecastDate",
    "Weekday",
    "MovingAverageBaseline",
    "WeekdayFactor",
    "ForecastUnits",
    "BacktestMAE",
    "BacktestWAPEPct",
]

ALERT_COLUMNS = [
    "StoreID",
    "SKU",
    "Category",
    "LatestActualDate",
    "LatestOnHandUnits",
    "LeadTimeDays",
    "MinDisplayUnits",
    "AvgForecastNext14D",
    "LeadTimeForecastUnits",
    "ReorderPointUnits",
    "CoverageDays14D",
    "RecommendedOrderUnits",
    "AlertLevel",
]


def build_expected(history: pd.DataFrame):
    history = history.copy()
    history["Date"] = pd.to_datetime(history["Date"])

    forecast_rows = []
    alert_rows = []

    for (store_id, sku), group in history.groupby(["StoreID", "SKU"], sort=True):
        group = group.sort_values("Date").reset_index(drop=True)
        category = group.at[0, "Category"]
        training = group.iloc[:TRAIN_DAYS].copy()
        holdout = group.iloc[TRAIN_DAYS:TRAIN_DAYS + HOLDOUT_DAYS].copy()

        baseline = training["UnitsSold"].iloc[-7:].mean()
        overall_mean = training["UnitsSold"].mean()
        weekday_factor = training.groupby(training["Date"].dt.weekday)["UnitsSold"].mean() / overall_mean

        holdout_pred = holdout["Date"].dt.weekday.map(weekday_factor) * baseline
        absolute_error = (holdout["UnitsSold"] - holdout_pred).abs()
        backtest_mae = round(float(absolute_error.mean()), 2)
        backtest_wape = round(float(absolute_error.sum() / holdout["UnitsSold"].sum() * 100), 2)

        latest_actual_date = group["Date"].max()
        future_dates = pd.date_range(latest_actual_date + pd.Timedelta(days=1), periods=FORECAST_DAYS, freq="D")
        future_forecast_units = []

        for forecast_date in future_dates:
            weekday_idx = forecast_date.weekday()
            weekday_value = float(weekday_factor.loc[weekday_idx])
            forecast_units = round(float(baseline * weekday_value), 2)
            future_forecast_units.append(forecast_units)
            forecast_rows.append(
                {
                    "StoreID": store_id,
                    "SKU": sku,
                    "Category": category,
                    "ForecastDate": forecast_date.date().isoformat(),
                    "Weekday": forecast_date.day_name(),
                    "MovingAverageBaseline": round(float(baseline), 2),
                    "WeekdayFactor": round(weekday_value, 4),
                    "ForecastUnits": forecast_units,
                    "BacktestMAE": backtest_mae,
                    "BacktestWAPEPct": backtest_wape,
                }
            )

        latest_on_hand = int(group.at[group.index[-1], "OnHandUnits"])
        lead_time_days = int(group.at[group.index[-1], "LeadTimeDays"])
        min_display_units = int(group.at[group.index[-1], "MinDisplayUnits"])
        avg_forecast = round(sum(future_forecast_units) / FORECAST_DAYS, 2)
        lead_time_forecast = round(sum(future_forecast_units[:lead_time_days]), 2)
        reorder_point = ceil(lead_time_forecast + min_display_units)
        coverage_days = round(latest_on_hand / avg_forecast, 2)
        recommended_order = max(0, ceil(reorder_point - latest_on_hand))

        if latest_on_hand < lead_time_forecast:
            alert_level = "Critical"
        elif latest_on_hand < reorder_point:
            alert_level = "Reorder"
        else:
            alert_level = "OK"

        alert_rows.append(
            {
                "StoreID": store_id,
                "SKU": sku,
                "Category": category,
                "LatestActualDate": latest_actual_date.date().isoformat(),
                "LatestOnHandUnits": latest_on_hand,
                "LeadTimeDays": lead_time_days,
                "MinDisplayUnits": min_display_units,
                "AvgForecastNext14D": avg_forecast,
                "LeadTimeForecastUnits": lead_time_forecast,
                "ReorderPointUnits": reorder_point,
                "CoverageDays14D": coverage_days,
                "RecommendedOrderUnits": recommended_order,
                "AlertLevel": alert_level,
            }
        )

    forecast_df = pd.DataFrame(forecast_rows, columns=FORECAST_COLUMNS)
    alert_df = pd.DataFrame(alert_rows, columns=ALERT_COLUMNS).sort_values(
        ["RecommendedOrderUnits", "StoreID", "SKU"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return forecast_df, alert_df


def test_workbook_has_required_sheets():
    workbook = pd.ExcelFile(OUTPUT_FILE)
    assert workbook.sheet_names == ["DailySales", "Forecast14D", "ReorderAlerts"]


def test_daily_sales_sheet_is_preserved():
    history = pd.read_excel(OUTPUT_FILE, sheet_name="DailySales")
    assert len(history) == 210
    assert history.iloc[0]["Date"] == "2025-01-06"
    assert history.iloc[-1]["Date"] == "2025-02-09"
    assert sorted(history["StoreID"].unique().tolist()) == ["S001", "S002", "S003"]
    assert sorted(history["SKU"].unique().tolist()) == ["APPLE_BAG", "MILK_1GAL"]


def test_forecast_sheet_matches_expected_values():
    history = pd.read_excel(OUTPUT_FILE, sheet_name="DailySales")
    forecast = pd.read_excel(OUTPUT_FILE, sheet_name="Forecast14D")
    expected_forecast, _ = build_expected(history)

    assert forecast.columns.tolist() == FORECAST_COLUMNS
    assert len(forecast) == 84
    assert_frame_equal(forecast, expected_forecast, check_dtype=False, atol=1e-6)


def test_reorder_alerts_match_expected_values():
    history = pd.read_excel(OUTPUT_FILE, sheet_name="DailySales")
    alerts = pd.read_excel(OUTPUT_FILE, sheet_name="ReorderAlerts")
    _, expected_alerts = build_expected(history)

    assert alerts.columns.tolist() == ALERT_COLUMNS
    assert len(alerts) == 6
    assert_frame_equal(alerts, expected_alerts, check_dtype=False, atol=1e-6)


def test_alert_mix_and_sort_order_are_correct():
    alerts = pd.read_excel(OUTPUT_FILE, sheet_name="ReorderAlerts")
    assert alerts["AlertLevel"].value_counts().to_dict() == {
        "Critical": 2,
        "Reorder": 2,
        "OK": 2,
    }
    assert alerts["RecommendedOrderUnits"].tolist() == [14, 12, 4, 2, 0, 0]
    top_row = alerts.iloc[0].to_dict()
    assert top_row["StoreID"] == "S003"
    assert top_row["SKU"] == "MILK_1GAL"
    assert top_row["AlertLevel"] == "Critical"
    assert top_row["CoverageDays14D"] == 1.76


def test_future_dates_cover_full_two_week_horizon():
    forecast = pd.read_excel(OUTPUT_FILE, sheet_name="Forecast14D")
    first_dates = forecast.groupby(["StoreID", "SKU"])["ForecastDate"].min().tolist()
    last_dates = forecast.groupby(["StoreID", "SKU"])["ForecastDate"].max().tolist()
    assert set(first_dates) == {"2025-02-10"}
    assert set(last_dates) == {"2025-02-23"}
