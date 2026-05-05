from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/root')
DATA = ROOT / 'data'
WORKSPACE = ROOT / 'workspace'
OUTPUT = ROOT / 'output'


def daterange(start: datetime, end: datetime):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> None:
    rng = np.random.default_rng(20260428)
    DATA.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    stations = pd.DataFrame([
        {'station_id': 'LK01', 'station_name': 'North Inlet', 'latitude': 43.122, 'longitude': -89.402, 'elevation_m': 260, 'timezone': 'America/Chicago'},
        {'station_id': 'LK02', 'station_name': 'Deep Basin', 'latitude': 43.094, 'longitude': -89.386, 'elevation_m': 259, 'timezone': 'America/Chicago'},
        {'station_id': 'LK03', 'station_name': 'Urban Shore', 'latitude': 43.071, 'longitude': -89.351, 'elevation_m': 258, 'timezone': 'America/Chicago'},
        {'station_id': 'LK04', 'station_name': 'South Wetland', 'latitude': 43.044, 'longitude': -89.424, 'elevation_m': 257, 'timezone': 'America/Chicago'},
    ])
    meta = stations[['station_id', 'station_name', 'latitude', 'longitude']].copy()
    meta['sensor_model'] = ['AquaTroll-200', 'AquaTroll-200', 'HydroCAT-EP', 'HydroCAT-EP']
    meta['installed_depth_m'] = [1.5, 4.0, 1.2, 2.2]
    meta['activated_at'] = ['2018-10-01', '2018-10-01', '2019-01-15', '2019-03-01']
    meta.to_csv(DATA / 'station_metadata.csv', index=False)

    start = datetime(2019, 1, 1)
    end = datetime(2022, 12, 31)
    days = list(daterange(start, end))

    weather_rows: list[dict[str, object]] = []
    hydro_rows: list[dict[str, object]] = []
    activity_rows: list[dict[str, object]] = []
    water_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []

    station_offsets = {'LK01': -0.25, 'LK02': -0.65, 'LK03': 0.35, 'LK04': -0.1}
    trend_per_year = {'LK01': 0.18, 'LK02': 0.12, 'LK03': 0.28, 'LK04': 0.16}
    depth_lag = {'LK01': 0.2, 'LK02': -0.6, 'LK03': 0.35, 'LK04': -0.05}

    for sidx, station in stations.iterrows():
        sid = station['station_id']
        for day in days:
            doy = day.timetuple().tm_yday
            years = (day - start).days / 365.25
            seasonal = math.sin(2 * math.pi * (doy - 105) / 365.25)
            air_temp = 9.5 + 14.0 * seasonal + 0.045 * (day.year - 2019) + station_offsets[sid] + rng.normal(0, 1.7)
            solar = max(30.0, 185 + 125 * math.sin(2 * math.pi * (doy - 80) / 365.25) + rng.normal(0, 24))
            wind = max(0.2, 4.2 + 1.5 * math.sin(2 * math.pi * (doy + 30) / 365.25) + rng.normal(0, 0.65))
            precip = max(0.0, rng.gamma(1.4, 2.2) - 1.1)
            inflow = max(1.0, 18 + 8.5 * math.sin(2 * math.pi * (doy + 20) / 365.25) + 0.55 * precip + rng.normal(0, 2.4))
            lake_level = 8.1 + 0.24 * math.sin(2 * math.pi * (doy + 60) / 365.25) + 0.012 * precip + rng.normal(0, 0.03)
            boat_count = max(0, int(18 + 17 * max(seasonal, 0) + (8 if sid == 'LK03' else 0) + rng.normal(0, 5)))
            shoreline_index = max(0.0, 0.35 + (0.26 if sid == 'LK03' else 0.05) + 0.12 * max(seasonal, 0) + rng.normal(0, 0.04))
            weather_rows.append({'station_id': sid, 'observed_date': day.date().isoformat(), 'air_temp_c': round(air_temp, 4), 'solar_w_m2': round(solar, 4), 'wind_speed_mps': round(wind, 4), 'precipitation_mm': round(precip, 4)})
            hydro_rows.append({'station_id': sid, 'observed_date': day.date().isoformat(), 'inflow_cms': round(inflow, 4), 'lake_level_m': round(lake_level, 4)})
            activity_rows.append({'station_id': sid, 'observed_date': day.date().isoformat(), 'boat_count': boat_count, 'shoreline_index': round(shoreline_index, 4)})

            base_water = 10.9 + 9.4 * math.sin(2 * math.pi * (doy - 125) / 365.25) + trend_per_year[sid] * years + depth_lag[sid]
            driver_effect = 0.16 * (air_temp - 9.5) + 0.0045 * (solar - 185) - 0.09 * (wind - 4.2) - 0.045 * (inflow - 18) + 0.055 * boat_count + 0.75 * (shoreline_index - 0.45)
            daily_mean = base_water + 0.22 * driver_effect + rng.normal(0, 0.18)
            for hour in [0, 6, 12, 18]:
                observed_at = day + timedelta(hours=hour)
                diurnal = 0.28 * math.sin(2 * math.pi * (hour - 7) / 24)
                temp_c = daily_mean + diurnal + rng.normal(0, 0.11)
                qc_flag = 'pass'
                sensor_status = 'ok'
                unit = 'C'
                if (sid, day.date().isoformat()) in {('LK02', '2020-08-14'), ('LK03', '2021-07-19'), ('LK01', '2022-02-03')}:
                    temp_c += 12.5
                    qc_flag = 'suspect'
                if sid == 'LK04' and day.month == 3 and day.day in {10, 11} and day.year == 2021:
                    qc_flag = 'fail'
                    sensor_status = 'fouled'
                if sid == 'LK01' and day.year == 2020 and day.month == 6 and day.day in {4, 5}:
                    sensor_status = 'maintenance'
                if sid == 'LK03' and day.year == 2021 and day.month == 8 and day.day in {20, 21, 22}:
                    temp_c += 3.8
                    sensor_status = 'drift'
                if sid == 'LK02' and day.year == 2022 and day.month == 1 and day.day in {15, 16}:
                    unit = 'F'
                    value = temp_c * 9 / 5 + 32
                else:
                    value = temp_c
                obs = {'station_id': sid, 'observed_at': observed_at.isoformat(), 'water_temp': round(float(value), 4), 'unit': unit, 'qc_flag': qc_flag, 'sensor_status': sensor_status, 'ingested_at': (observed_at + timedelta(minutes=7)).isoformat()}
                water_rows.append(obs)
                if sid == 'LK03' and day.year == 2020 and day.month == 9 and day.day == 3 and hour == 12:
                    dup = obs.copy()
                    dup['water_temp'] = round(float(value) + 0.7, 4)
                    dup['ingested_at'] = (observed_at + timedelta(minutes=1)).isoformat()
                    water_rows.append(dup)
                if sid == 'LK01' and day.year == 2021 and day.month == 5 and day.day == 18 and hour == 6:
                    dup = obs.copy()
                    dup['water_temp'] = round(float(value) - 0.5, 4)
                    dup['ingested_at'] = (observed_at + timedelta(minutes=1)).isoformat()
                    water_rows.append(dup)

    events = [
        ('LK01', '2020-06-04T00:00:00', '2020-06-06T00:00:00', 'maintenance'),
        ('LK03', '2021-08-20T00:00:00', '2021-08-23T00:00:00', 'sensor_drift'),
        ('LK02', '2022-01-14T00:00:00', '2022-01-18T00:00:00', 'ice_cover'),
        ('LK04', '2021-03-10T00:00:00', '2021-03-12T00:00:00', 'maintenance'),
    ]
    for idx, (sid, st, en, kind) in enumerate(events, 1):
        event_rows.append({'event_id': f'E{idx:03d}', 'station_id': sid, 'start_at': st, 'end_at': en, 'event_type': kind})
        window_rows.append({'station_id': sid, 'start_at': st, 'end_at': en, 'event_type': kind, 'exclude_from_analysis': True})
    pd.DataFrame(window_rows).to_csv(DATA / 'event_windows.csv', index=False)

    db = DATA / 'observatory.db'
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(db)
    stations.to_sql('stations', conn, index=False, if_exists='replace')
    pd.DataFrame(water_rows).reset_index(names='obs_id').to_sql('water_temperature', conn, index=False, if_exists='replace')
    pd.DataFrame(weather_rows).to_sql('weather_daily', conn, index=False, if_exists='replace')
    pd.DataFrame(hydro_rows).to_sql('hydrology_daily', conn, index=False, if_exists='replace')
    pd.DataFrame(activity_rows).to_sql('human_activity_daily', conn, index=False, if_exists='replace')
    pd.DataFrame(event_rows).to_sql('maintenance_events', conn, index=False, if_exists='replace')
    conn.execute('CREATE INDEX idx_water_station_time ON water_temperature(station_id, observed_at)')
    conn.execute('CREATE INDEX idx_weather_station_date ON weather_daily(station_id, observed_date)')
    conn.commit()
    conn.close()

    schema = {
        'station_trends.csv': {
            'columns': ['station_id', 'station_name', 'start_date', 'end_date', 'n_days', 'valid_observations', 'missing_rate', 'outlier_rate', 'temp_slope_c_per_year', 'p_value', 'trend_method']
        },
        'driver_attribution.csv': {
            'columns': ['category', 'contribution_pct', 'signed_effect', 'rank', 'n_features'],
            'categories': ['Heat', 'Flow', 'Wind', 'Human']
        },
        'run_summary.json': {
            'required_top_level': ['dataset', 'quality_control', 'trend', 'attribution', 'warnings']
        }
    }
    (DATA / 'expected_schema.json').write_text(json.dumps(schema, indent=2), encoding='utf-8')

    run_analysis = WORKSPACE / 'run_analysis.py'
    run_analysis.write_text('''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CATEGORIES = ["Heat", "Flow", "Wind", "Human"]


def load_raw(data_dir: Path):
    conn = sqlite3.connect(data_dir / "observatory.db")
    water = pd.read_sql_query("SELECT * FROM water_temperature", conn, parse_dates=["observed_at", "ingested_at"])
    stations = pd.read_sql_query("SELECT * FROM stations", conn)
    weather = pd.read_sql_query("SELECT * FROM weather_daily", conn, parse_dates=["observed_date"])
    hydro = pd.read_sql_query("SELECT * FROM hydrology_daily", conn, parse_dates=["observed_date"])
    activity = pd.read_sql_query("SELECT * FROM human_activity_daily", conn, parse_dates=["observed_date"])
    conn.close()
    meta = pd.read_csv(data_dir / "station_metadata.csv")
    return water, stations, weather, hydro, activity, meta


def naive_daily(data_dir: Path):
    water, stations, weather, hydro, activity, meta = load_raw(data_dir)
    # BUGS: keeps duplicate observations, does not convert Fahrenheit, ignores event windows,
    # ignores suspect/drift statuses, and uses mean/OLS that is sensitive to outliers.
    water["date"] = water["observed_at"].dt.floor("D")
    daily = water.groupby(["station_id", "date"], as_index=False).agg(
        temp_c=("water_temp", "mean"),
        valid_observations=("water_temp", "size"),
    )
    daily = daily.merge(stations[["station_id", "station_name"]], on="station_id", how="left")
    weather = weather.rename(columns={"observed_date": "date"})
    hydro = hydro.rename(columns={"observed_date": "date"})
    activity = activity.rename(columns={"observed_date": "date"})
    daily = daily.merge(weather, on=["station_id", "date"], how="left")
    daily = daily.merge(hydro, on=["station_id", "date"], how="left")
    daily = daily.merge(activity, on=["station_id", "date"], how="left")
    return daily, water, stations


def write_outputs(data_dir: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    daily, water, stations = naive_daily(data_dir)
    trend_rows = []
    for sid, group in daily.groupby("station_id"):
        group = group.sort_values("date")
        x = (group["date"] - group["date"].min()).dt.days.to_numpy(dtype=float) / 365.25
        y = group["temp_c"].to_numpy(dtype=float)
        slope, intercept, r, p, se = stats.linregress(x, y)
        trend_rows.append({
            "station_id": sid,
            "station_name": group["station_name"].iloc[0],
            "start_date": group["date"].min().date().isoformat(),
            "end_date": group["date"].max().date().isoformat(),
            "n_days": int(len(group)),
            "valid_observations": int(group["valid_observations"].sum()),
            "missing_rate": 0.0,
            "outlier_rate": 0.0,
            "temp_slope_c_per_year": round(float(slope), 6),
            "p_value": round(float(p), 6),
            "trend_method": "ordinary_least_squares",
        })
    pd.DataFrame(trend_rows).to_csv(output / "station_trends.csv", index=False)

    model = daily.dropna(subset=["temp_c", "air_temp_c", "solar_w_m2", "wind_speed_mps", "inflow_cms", "boat_count"])
    feature_map = {
        "Heat": ["air_temp_c", "solar_w_m2"],
        "Flow": ["inflow_cms", "lake_level_m"],
        "Wind": ["wind_speed_mps"],
        "Human": ["boat_count", "shoreline_index"],
    }
    features = [f for vals in feature_map.values() for f in vals]
    X_raw = model[features].to_numpy(dtype=float)
    X = (X_raw - X_raw.mean(axis=0)) / X_raw.std(axis=0, ddof=0)
    y = model["temp_c"].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(X)), X])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    coefs = beta[1:]
    pred = design @ beta
    raw = np.abs(coefs)
    rows = []
    for cat, cols in feature_map.items():
        idx = [features.index(c) for c in cols]
        rows.append({"category": cat, "raw": float(raw[idx].sum()), "signed_effect": float(coefs[idx].sum()), "n_features": len(cols)})
    total = sum(r["raw"] for r in rows) or 1.0
    for r in rows:
        r["contribution_pct"] = round(100 * r.pop("raw") / total, 6)
    rows.sort(key=lambda row: -row["contribution_pct"])
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    pd.DataFrame(rows)[["category", "contribution_pct", "signed_effect", "rank", "n_features"]].to_csv(output / "driver_attribution.csv", index=False)

    report = {
        "dataset": {"stations": int(stations["station_id"].nunique()), "raw_observations": int(len(water)), "daily_records": int(len(daily)), "analysis_start": str(daily["date"].min().date()), "analysis_end": str(daily["date"].max().date())},
        "quality_control": {"dropped_duplicate_rows": 0, "dropped_qc_rows": 0, "dropped_event_window_rows": 0, "imputed_daily_values": 0},
        "trend": {"method": "ordinary_least_squares", "stations_with_significant_warming": int((pd.DataFrame(trend_rows)["p_value"] < 0.05).sum()), "median_slope_c_per_year": float(pd.DataFrame(trend_rows)["temp_slope_c_per_year"].median())},
        "attribution": {"method": "standardized_linear_coefficients", "dominant_category": rows[0]["category"], "model_r2": float(1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)), "contribution_sum": float(sum(r["contribution_pct"] for r in rows))},
        "warnings": ["naive pipeline output; review quality-control assumptions"],
    }
    (output / "run_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="/root/data")
    parser.add_argument("--output", default="/root/output")
    args = parser.parse_args()
    write_outputs(Path(args.data), Path(args.output))


if __name__ == "__main__":
    main()
''', encoding='utf-8')
    run_analysis.chmod(0o755)


if __name__ == '__main__':
    main()
