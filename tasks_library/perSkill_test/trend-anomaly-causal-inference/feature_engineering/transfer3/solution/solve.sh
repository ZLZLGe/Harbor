#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, '/root/.codex/skills/feature_engineering/scripts')
from feature_engineering import FeatureEngineeringPipeline, FeatureEngineeringStrategies

config = json.loads(Path('/root/data/task_config.json').read_text())
df = pd.read_csv(config['input_file'])

pipeline = FeatureEngineeringPipeline(name=config['pipeline_name'])
for step in config['steps']:
    pipeline.add_step(
        getattr(FeatureEngineeringStrategies, step['strategy']),
        description=step['description'],
        **step.get('kwargs', {}),
    )

engineered = pipeline.execute(df, verbose=False)

id_col = config['id_column']
for step in config['steps']:
    if step['strategy'] != 'convert_to_binary':
        continue
    for column in step.get('kwargs', {}).get('columns', []):
        if column not in engineered.columns or pd.api.types.is_numeric_dtype(engineered[column]):
            continue
        non_null = sorted(engineered[column].dropna().astype(str).unique().tolist())
        if len(non_null) == 2:
            mapping = {non_null[0]: 0.0, non_null[1]: 1.0}
            engineered[column] = engineered[column].astype(str).map(mapping)

feature_columns = [column for column in engineered.columns if column != id_col]
output_df = engineered[[id_col] + feature_columns].copy()

output_path = Path(config['output_file'])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_df.to_csv(output_path, index=False)

summary = {
    'row_count': int(len(output_df)),
    'columns': output_df.columns.tolist(),
    'engineered_feature_count': int(len(feature_columns)),
}
Path(config['summary_file']).write_text(json.dumps(summary, indent=2))
PY
