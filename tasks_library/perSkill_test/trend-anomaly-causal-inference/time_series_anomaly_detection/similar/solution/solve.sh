#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, '/root/.codex/skills/time_series_anomaly_detection/scripts')
from anomaly_detection import TimeSeriesAnomalyDetector

config = json.loads(Path('/root/data/task_config.json').read_text())
df = pd.read_csv(config['input_file'])

detector = TimeSeriesAnomalyDetector(
    min_training_days=config.get('min_training_days', 45),
    confidence_interval=config.get('confidence_interval', 0.68),
    changepoint_prior_scale=config.get('changepoint_prior_scale', 0.1),
    seasonality_prior_scale=config.get('seasonality_prior_scale', 10.0),
)

results = detector.detect_anomalies(
    df=df,
    date_col=config['date_col'],
    category_col=config['category_col'],
    value_col=config['value_col'],
    cutoff_date=config['cutoff_date'],
    prediction_start=config.get('prediction_start'),
    prediction_end=config['prediction_end'],
    agg_func=config.get('agg_func', 'sum'),
)

summary = results['anomaly_summary'][[config['category_col'], 'Anomaly_Index']].copy()
summary = summary.rename(columns={config['category_col']: 'Category'})
summary = summary.sort_values('Anomaly_Index', ascending=False).reset_index(drop=True)
summary['Anomaly_Index'] = summary['Anomaly_Index'].round(6)

output_path = Path(config['output_file'])
output_path.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(output_path, index=False)

meta = {
    'row_count': int(len(summary)),
    'top_category': summary.iloc[0]['Category'],
    'bottom_category': summary.iloc[-1]['Category'],
}
Path(config['summary_file']).write_text(json.dumps(meta, indent=2))
PY
