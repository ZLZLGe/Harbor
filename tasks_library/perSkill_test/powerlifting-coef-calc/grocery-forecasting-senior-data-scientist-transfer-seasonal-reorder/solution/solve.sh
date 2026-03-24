#!/bin/bash

set -euo pipefail

python3 - <<'PY'
from math import ceil
from pathlib import Path

import pandas as pd
from openpyxl import Workbook


OUTPUT_FILE = Path("/root/data/store_reorder_forecast.xlsx")
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


def build_outputs(history: pd.DataFrame):
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


def write_sheet(worksheet, dataframe: pd.DataFrame):
    worksheet.append(list(dataframe.columns))
    for row in dataframe.itertuples(index=False, name=None):
        worksheet.append(list(row))


history_df = pd.read_excel(OUTPUT_FILE, sheet_name="DailySales")
forecast_df, alert_df = build_outputs(history_df)

workbook = Workbook()
history_sheet = workbook.active
history_sheet.title = "DailySales"
forecast_sheet = workbook.create_sheet("Forecast14D")
alert_sheet = workbook.create_sheet("ReorderAlerts")

write_sheet(history_sheet, history_df)
write_sheet(forecast_sheet, forecast_df)
write_sheet(alert_sheet, alert_df)

workbook.save(OUTPUT_FILE)
PY
