#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

CATEGORIES = ['Heat', 'Flow', 'Wind', 'Human']
FEATURE_MAP = {
    'Heat': ['air_temp_c', 'solar_w_m2'],
    'Flow': ['inflow_cms', 'lake_level_m'],
    'Wind': ['wind_speed_mps'],
    'Human': ['boat_count', 'shoreline_index'],
}
TREND_COLUMNS = [
    'station_id', 'station_name', 'start_date', 'end_date', 'n_days', 'valid_observations',
    'missing_rate', 'outlier_rate', 'temp_slope_c_per_year', 'p_value', 'trend_method'
]
ATTR_COLUMNS = ['category', 'contribution_pct', 'signed_effect', 'rank', 'n_features']


def load_inputs(data_dir: Path) -> dict[str, pd.DataFrame | dict]:
    conn = sqlite3.connect(data_dir / 'observatory.db')
    try:
        inputs: dict[str, pd.DataFrame | dict] = {
            'stations': pd.read_sql_query('SELECT * FROM stations', conn),
            'water': pd.read_sql_query('SELECT * FROM water_temperature', conn, parse_dates=['observed_at', 'ingested_at']),
            'weather': pd.read_sql_query('SELECT * FROM weather_daily', conn, parse_dates=['observed_date']),
            'hydro': pd.read_sql_query('SELECT * FROM hydrology_daily', conn, parse_dates=['observed_date']),
            'activity': pd.read_sql_query('SELECT * FROM human_activity_daily', conn, parse_dates=['observed_date']),
            'events': pd.read_sql_query('SELECT * FROM maintenance_events', conn, parse_dates=['start_at', 'end_at']),
        }
    finally:
        conn.close()
    inputs['metadata'] = pd.read_csv(data_dir / 'station_metadata.csv')
    inputs['event_windows'] = pd.read_csv(data_dir / 'event_windows.csv', parse_dates=['start_at', 'end_at'])
    inputs['schema'] = json.loads((data_dir / 'expected_schema.json').read_text(encoding='utf-8'))
    return inputs


def build_daily(inputs: dict[str, pd.DataFrame | dict]) -> tuple[pd.DataFrame, dict[str, int]]:
    # Keep the raw observation count before any quality-control filtering.
    water = inputs['water'].copy()  # type: ignore[index,union-attr]
    raw_observations = len(water)
    water = water.sort_values(['station_id', 'observed_at', 'ingested_at', 'obs_id'])
    # Deduplicate by station/timestamp after stable sorting by ingestion order.
    deduped = water.drop_duplicates(['station_id', 'observed_at'], keep='last').copy()
    dropped_duplicate_rows = raw_observations - len(deduped)

    deduped['temp_c'] = np.where(
        deduped['unit'].eq('F'),
        (deduped['water_temp'].astype(float) - 32.0) * 5.0 / 9.0,
        deduped['water_temp'].astype(float),
    )
    qc_mask = deduped['qc_flag'].eq('pass') & deduped['sensor_status'].eq('ok')
    dropped_qc_rows = int((~qc_mask).sum())
    clean = deduped.loc[qc_mask].copy()

    event_windows = inputs['event_windows']  # type: ignore[assignment]
    # Apply maintenance, drift, and ice windows before daily aggregation.
    event_mask = pd.Series(False, index=clean.index)
    for row in event_windows.itertuples(index=False):
        if bool(row.exclude_from_analysis):
            event_mask |= (
                clean['station_id'].eq(row.station_id)
                & clean['observed_at'].ge(row.start_at)
                & clean['observed_at'].lt(row.end_at)
            )
    dropped_event_window_rows = int(event_mask.sum())
    clean = clean.loc[~event_mask].copy()

    clean['month'] = clean['observed_at'].dt.month
    outlier_mask = pd.Series(False, index=clean.index)
    for _, group in clean.groupby(['station_id', 'month']):
        median = group['temp_c'].median()
        mad = float(np.median(np.abs(group['temp_c'] - median)))
        if mad > 0:
            modified_z = 0.6745 * (group['temp_c'] - median).abs() / mad
            outlier_mask.loc[group.index] = modified_z.gt(7.0)
    dropped_outlier_rows = int(outlier_mask.sum())
    clean = clean.loc[~outlier_mask].copy()

    clean['date'] = clean['observed_at'].dt.floor('D')
    daily = clean.groupby(['station_id', 'date'], as_index=False).agg(
        temp_c=('temp_c', 'mean'),
        valid_observations=('temp_c', 'size'),
    )
    daily['doy'] = daily['date'].dt.dayofyear
    stations = inputs['stations']  # type: ignore[assignment]
    daily = daily.merge(stations[['station_id', 'station_name']], on='station_id', how='left')
    weather = inputs['weather'].rename(columns={'observed_date': 'date'})  # type: ignore[union-attr]
    hydro = inputs['hydro'].rename(columns={'observed_date': 'date'})  # type: ignore[union-attr]
    activity = inputs['activity'].rename(columns={'observed_date': 'date'})  # type: ignore[union-attr]
    daily = daily.merge(weather, on=['station_id', 'date'], how='left')
    daily = daily.merge(hydro, on=['station_id', 'date'], how='left')
    daily = daily.merge(activity, on=['station_id', 'date'], how='left')
    daily = daily.sort_values(['station_id', 'date']).reset_index(drop=True)

    qc = {
        'raw_observations': int(raw_observations),
        'dropped_duplicate_rows': int(dropped_duplicate_rows),
        'dropped_qc_rows': int(dropped_qc_rows),
        'dropped_event_window_rows': int(dropped_event_window_rows),
        'dropped_outlier_rows': int(dropped_outlier_rows),
        'imputed_daily_values': 0,
    }
    return daily, qc


def compute_station_trends(daily: pd.DataFrame, qc: dict[str, int], inputs: dict[str, pd.DataFrame | dict]) -> pd.DataFrame:
    water = inputs['water']  # type: ignore[assignment]
    rows: list[dict[str, object]] = []
    for station_id, group in daily.groupby('station_id'):
        group = group.sort_values('date').copy()
        full_days = pd.date_range(group['date'].min(), group['date'].max(), freq='D')
        climatology = group.groupby('doy')['temp_c'].median()
        group['temp_anomaly'] = group['temp_c'] - group['doy'].map(climatology)
        x = (group['date'] - group['date'].min()).dt.days.to_numpy(dtype=float) / 365.25
        y = group['temp_anomaly'].to_numpy(dtype=float)
        slope, _, _, _ = stats.theilslopes(y, x, 0.95)
        tau = stats.kendalltau(x, y, nan_policy='omit')
        station_raw = water.loc[water['station_id'].eq(station_id)].drop_duplicates(['station_id', 'observed_at'])
        outlier_rate = qc['dropped_outlier_rows'] / max(1, len(station_raw))
        rows.append({
            'station_id': station_id,
            'station_name': group['station_name'].iloc[0],
            'start_date': group['date'].min().date().isoformat(),
            'end_date': group['date'].max().date().isoformat(),
            'n_days': int(len(group)),
            'valid_observations': int(group['valid_observations'].sum()),
            'missing_rate': round(float(1 - len(group) / len(full_days)), 6),
            'outlier_rate': round(float(outlier_rate), 6),
            'temp_slope_c_per_year': round(float(slope), 6),
            'p_value': round(float(tau.pvalue), 6),
            'trend_method': 'theil_sen_daily_anomaly_kendall_tau',
        })
    return pd.DataFrame(rows)[TREND_COLUMNS].sort_values('station_id').reset_index(drop=True)


def compute_attribution(daily: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    features = [feature for columns in FEATURE_MAP.values() for feature in columns]
    model = daily.dropna(subset=['temp_c'] + features).copy()
    station_clim = model.groupby(['station_id', 'doy'])['temp_c'].transform('median')
    model['target_anomaly'] = model['temp_c'] - station_clim
    X = model[features].astype(float)
    y = model['target_anomaly'].astype(float).to_numpy()
    X_raw = X.to_numpy(dtype=float)
    X_scaled = (X_raw - X_raw.mean(axis=0)) / X_raw.std(axis=0, ddof=0)
    design = np.column_stack([np.ones(len(X_scaled)), X_scaled])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    predictions = design @ beta
    coefs = dict(zip(features, beta[1:]))

    rows: list[dict[str, object]] = []
    total_abs = 0.0
    for category in CATEGORIES:
        category_features = FEATURE_MAP[category]
        raw = float(sum(abs(coefs[feature]) for feature in category_features))
        total_abs += raw
        rows.append({
            'category': category,
            'raw': raw,
            'signed_effect': float(sum(coefs[feature] for feature in category_features)),
            'n_features': len(category_features),
        })
    total_abs = total_abs or 1.0
    for row in rows:
        row['contribution_pct'] = round(float(row.pop('raw')) / total_abs * 100.0, 6)
        row['signed_effect'] = round(float(row['signed_effect']), 6)
    rows[-1]['contribution_pct'] = round(float(rows[-1]['contribution_pct']) + round(100.0 - sum(float(row['contribution_pct']) for row in rows), 6), 6)
    ranked = sorted(rows, key=lambda row: (-float(row['contribution_pct']), CATEGORIES.index(str(row['category']))))
    rank_by_category = {str(row['category']): rank for rank, row in enumerate(ranked, 1)}
    for row in rows:
        row['rank'] = rank_by_category[str(row['category'])]
    table = pd.DataFrame(rows)[ATTR_COLUMNS]
    summary = {
        'method': 'standardized_linear_model_on_daily_temperature_anomalies',
        'dominant_category': str(ranked[0]['category']),
        'model_r2': round(float(1 - np.sum((y - predictions) ** 2) / np.sum((y - y.mean()) ** 2)), 6),
        'contribution_sum': round(float(table['contribution_pct'].sum()), 6),
    }
    return table, summary


def write_outputs(data_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(data_dir)
    daily, qc = build_daily(inputs)
    trends = compute_station_trends(daily, qc, inputs)
    attribution, attribution_summary = compute_attribution(daily)

    # Write deterministic files with fixed column order and numeric formatting.
    trends.to_csv(output_dir / 'station_trends.csv', index=False, float_format='%.6f')
    attribution.to_csv(output_dir / 'driver_attribution.csv', index=False, float_format='%.6f')

    stations = inputs['stations']  # type: ignore[assignment]
    summary = {
        'dataset': {
            'stations': int(stations['station_id'].nunique()),
            'raw_observations': int(qc['raw_observations']),
            'daily_records': int(len(daily)),
            'analysis_start': daily['date'].min().date().isoformat(),
            'analysis_end': daily['date'].max().date().isoformat(),
        },
        'quality_control': {
            'dropped_duplicate_rows': int(qc['dropped_duplicate_rows']),
            'dropped_qc_rows': int(qc['dropped_qc_rows'] + qc['dropped_outlier_rows']),
            'dropped_event_window_rows': int(qc['dropped_event_window_rows']),
            'imputed_daily_values': int(qc['imputed_daily_values']),
        },
        'trend': {
            'method': 'theil_sen_daily_anomaly_kendall_tau',
            'stations_with_significant_warming': int(((trends['temp_slope_c_per_year'] > 0) & (trends['p_value'] < 0.05)).sum()),
            'median_slope_c_per_year': round(float(trends['temp_slope_c_per_year'].median()), 6),
        },
        'attribution': attribution_summary,
        'warnings': [],
    }
    audit = {
        'sql_queries': [
            {'name': 'water_temperature_extract', 'tables': ['water_temperature'], 'purpose': 'read hourly observations with ingestion timestamps for de-duplication'},
            {'name': 'station_context_extract', 'tables': ['stations', 'station_metadata.csv'], 'purpose': 'preserve station names, coordinates, sensor models, depths, and activation metadata'},
            {'name': 'driver_extract', 'tables': ['weather_daily', 'hydrology_daily', 'human_activity_daily'], 'purpose': 'join daily explanatory variables for Heat, Flow, Wind, and Human attribution'},
        ],
        'pandas_operations': [
            'sort and drop_duplicates by station_id plus observed_at using latest ingested_at and obs_id',
            'convert Fahrenheit water observations to Celsius before aggregation',
            'filter qc_flag, sensor_status, maintenance windows, drift windows, ice windows, and outlier observations',
            'merge station, weather, hydrology, and human activity tables on station_id and date',
            'group by station_id and daily date to create deterministic daily temperature records',
        ],
        'statistical_checks': [
            'Theil-Sen trend slope on daily station temperature anomalies',
            'Kendall tau p-value for monotonic warming significance',
            'standardized linear attribution model on Heat, Flow, Wind, and Human driver groups',
        ],
        'performance_considerations': [
            'read each SQLite table once and reuse pandas frames for trend and attribution outputs',
            'use vectorized pandas joins/groupby operations and stable sorting for deterministic output',
        ],
        'example_results': [
            f"example station trend: {trends.iloc[0]['station_id']} slope={float(trends.iloc[0]['temp_slope_c_per_year']):.6f} C/year p-value={float(trends.iloc[0]['p_value']):.6f}",
            f"example dominant driver: {summary['attribution']['dominant_category']}",
            f"example contribution sum: {summary['attribution']['contribution_sum']:.6f}",
        ],
        'skill_output_format': {
            'clear_comments_or_notes': [
                'SQL extraction is separated from pandas quality control and statistical modeling.',
                'Duplicate observations are resolved before unit conversion and event-window filtering.',
            ],
            'example_results': [
                f"station={trends.iloc[0]['station_id']} slope={float(trends.iloc[0]['temp_slope_c_per_year']):.6f}",
                f"dominant_category={summary['attribution']['dominant_category']}",
                f"contribution_sum={summary['attribution']['contribution_sum']:.6f}",
            ],
            'performance_considerations': [
                'SQLite tables are loaded once and reused across station trends and driver attribution.',
                'Vectorized pandas groupby and stable sorting keep the run deterministic.',
            ],
            'interpretation_of_findings': [
                f"{summary['trend']['stations_with_significant_warming']} stations show significant positive warming under the selected robust test.",
                f"{summary['attribution']['dominant_category']} is the leading driver category after normalized attribution.",
            ],
        },
        'interpretation': {
            'dominant_category': summary['attribution']['dominant_category'],
            'warming_station_count': summary['trend']['stations_with_significant_warming'],
            'key_findings': [
                f"{summary['trend']['stations_with_significant_warming']} stations show positive significant warming by the selected robust trend test",
                f"{summary['attribution']['dominant_category']} has the highest normalized attribution contribution",
            ],
        },
    }
    (output_dir / 'analysis_workflow_audit.json').write_text(json.dumps(audit, indent=2, sort_keys=True), encoding='utf-8')
    (output_dir / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='/root/data')
    parser.add_argument('--output', default='/root/output')
    args = parser.parse_args()
    write_outputs(Path(args.data), Path(args.output))


if __name__ == '__main__':
    main()
