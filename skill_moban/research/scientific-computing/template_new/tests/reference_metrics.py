from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path('/root/data')
CATEGORIES = ['Heat', 'Flow', 'Wind', 'Human']
FEATURE_MAP = {
    'Heat': ['air_temp_c', 'solar_w_m2'],
    'Flow': ['inflow_cms', 'lake_level_m'],
    'Wind': ['wind_speed_mps'],
    'Human': ['boat_count', 'shoreline_index'],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_inputs(data_dir: Path = DATA) -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(data_dir / 'observatory.db')
    inputs = {
        'stations': pd.read_sql_query('SELECT * FROM stations', conn),
        'water': pd.read_sql_query('SELECT * FROM water_temperature', conn, parse_dates=['observed_at', 'ingested_at']),
        'weather': pd.read_sql_query('SELECT * FROM weather_daily', conn, parse_dates=['observed_date']),
        'hydro': pd.read_sql_query('SELECT * FROM hydrology_daily', conn, parse_dates=['observed_date']),
        'activity': pd.read_sql_query('SELECT * FROM human_activity_daily', conn, parse_dates=['observed_date']),
        'events_db': pd.read_sql_query('SELECT * FROM maintenance_events', conn, parse_dates=['start_at', 'end_at']),
    }
    conn.close()
    inputs['metadata'] = pd.read_csv(data_dir / 'station_metadata.csv')
    inputs['event_windows'] = pd.read_csv(data_dir / 'event_windows.csv', parse_dates=['start_at', 'end_at'])
    inputs['schema'] = json.loads((data_dir / 'expected_schema.json').read_text(encoding='utf-8'))
    return inputs


def qc_daily(inputs: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, int]]:
    water = inputs['water'].copy()
    raw_rows = len(water)
    water = water.sort_values(['station_id', 'observed_at', 'ingested_at', 'obs_id'])
    deduped = water.drop_duplicates(['station_id', 'observed_at'], keep='last').copy()
    dropped_duplicate_rows = raw_rows - len(deduped)

    deduped['temp_c'] = np.where(
        deduped['unit'].eq('F'),
        (deduped['water_temp'].astype(float) - 32.0) * 5.0 / 9.0,
        deduped['water_temp'].astype(float),
    )
    qc_mask = deduped['qc_flag'].eq('pass') & deduped['sensor_status'].eq('ok')
    dropped_qc_rows = int((~qc_mask).sum())
    clean = deduped.loc[qc_mask].copy()

    event_mask = pd.Series(False, index=clean.index)
    for row in inputs['event_windows'].itertuples(index=False):
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
    for (_, _), group in clean.groupby(['station_id', 'month']):
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
    daily = daily.merge(inputs['stations'][['station_id', 'station_name']], on='station_id', how='left')
    weather = inputs['weather'].rename(columns={'observed_date': 'date'})
    hydro = inputs['hydro'].rename(columns={'observed_date': 'date'})
    activity = inputs['activity'].rename(columns={'observed_date': 'date'})
    daily = daily.merge(weather, on=['station_id', 'date'], how='left')
    daily = daily.merge(hydro, on=['station_id', 'date'], how='left')
    daily = daily.merge(activity, on=['station_id', 'date'], how='left')
    daily = daily.sort_values(['station_id', 'date']).reset_index(drop=True)

    stats_dict = {
        'raw_observations': int(raw_rows),
        'dropped_duplicate_rows': int(dropped_duplicate_rows),
        'dropped_qc_rows': int(dropped_qc_rows),
        'dropped_event_window_rows': int(dropped_event_window_rows),
        'dropped_outlier_rows': int(dropped_outlier_rows),
        'imputed_daily_values': 0,
    }
    return daily, stats_dict


def station_trends(daily: pd.DataFrame, qc: dict[str, int]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for sid, group in daily.groupby('station_id'):
        group = group.sort_values('date').copy()
        full_days = pd.date_range(group['date'].min(), group['date'].max(), freq='D')
        climatology = group.groupby('doy')['temp_c'].median()
        group['temp_anomaly'] = group['temp_c'] - group['doy'].map(climatology)
        x = (group['date'] - group['date'].min()).dt.days.to_numpy(dtype=float) / 365.25
        y = group['temp_anomaly'].to_numpy(dtype=float)
        slope, intercept, low, high = stats.theilslopes(y, x, 0.95)
        tau = stats.kendalltau(x, y, nan_policy='omit')
        original = len(load_inputs()['water'].query('station_id == @sid').drop_duplicates(['station_id', 'observed_at']))
        outlier_rate = qc['dropped_outlier_rows'] / max(1, original)
        rows.append({
            'station_id': sid,
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
    return pd.DataFrame(rows).sort_values('station_id').reset_index(drop=True)


def attribution(daily: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    model = daily.dropna(subset=['temp_c'] + [c for cols in FEATURE_MAP.values() for c in cols]).copy()
    station_clim = model.groupby(['station_id', 'doy'])['temp_c'].transform('median')
    model['target_anomaly'] = model['temp_c'] - station_clim
    features = [feature for columns in FEATURE_MAP.values() for feature in columns]
    X = model[features].astype(float)
    y = model['target_anomaly'].astype(float).to_numpy()
    X_raw = X.to_numpy(dtype=float)
    X_scaled = (X_raw - X_raw.mean(axis=0)) / X_raw.std(axis=0, ddof=0)
    design = np.column_stack([np.ones(len(X_scaled)), X_scaled])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    pred = design @ beta
    coefs = dict(zip(features, beta[1:]))

    raw_rows: list[dict[str, object]] = []
    total_abs = 0.0
    for category in CATEGORIES:
        cols = FEATURE_MAP[category]
        raw = float(sum(abs(coefs[c]) for c in cols))
        signed = float(sum(coefs[c] for c in cols))
        total_abs += raw
        raw_rows.append({'category': category, 'raw': raw, 'signed_effect': signed, 'n_features': len(cols)})
    total_abs = total_abs or 1.0
    for row in raw_rows:
        row['contribution_pct'] = round(row['raw'] / total_abs * 100.0, 6)
        del row['raw']
    adjustment = round(100.0 - sum(float(r['contribution_pct']) for r in raw_rows), 6)
    raw_rows[-1]['contribution_pct'] = round(float(raw_rows[-1]['contribution_pct']) + adjustment, 6)
    rank_order = sorted(raw_rows, key=lambda r: (-float(r['contribution_pct']), CATEGORIES.index(str(r['category']))))
    rank_map = {str(row['category']): rank for rank, row in enumerate(rank_order, 1)}
    for row in raw_rows:
        row['signed_effect'] = round(float(row['signed_effect']), 6)
        row['rank'] = rank_map[str(row['category'])]
    attr = pd.DataFrame(raw_rows)[['category', 'contribution_pct', 'signed_effect', 'rank', 'n_features']]
    summary = {
        'method': 'standardized_linear_model_on_daily_temperature_anomalies',
        'dominant_category': str(rank_order[0]['category']),
        'model_r2': round(float(1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)), 6),
        'contribution_sum': round(float(attr['contribution_pct'].sum()), 6),
    }
    return attr, summary


def expected_bundle(data_dir: Path = DATA) -> dict[str, object]:
    inputs = load_inputs(data_dir)
    daily, qc = qc_daily(inputs)
    trends = station_trends(daily, qc)
    attr, attr_summary = attribution(daily)
    summary = {
        'dataset': {
            'stations': int(inputs['stations']['station_id'].nunique()),
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
        'attribution': attr_summary,
    }
    return {'daily': daily, 'trends': trends, 'attribution': attr, 'summary': summary, 'inputs': inputs}
