#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, '/root/.codex/skills/did_causal_analysis/scripts')
from did_analysis import DIDAnalyzer

config = json.loads(Path('/root/data/task_config.json').read_text())
intensive_df = pd.read_csv(config['intensive_file'])
extensive_df = pd.read_csv(config['extensive_file'])

analyzer = DIDAnalyzer(
    min_sample_ratio=config.get('min_sample_ratio', 1),
    significance_level=config.get('significance_level', 0.05),
    min_group_size=config.get('min_group_size', 1),
)

intensive_results = analyzer.intensive_margin(
    intensive_df,
    features=config['features'],
    value_col=config['intensive_value_col'],
    top_n=config.get('top_n', 3),
    sort_by='estimate',
    asc=config.get('ascending', False),
)
extensive_results = analyzer.extensive_margin(
    extensive_df,
    features=config['features'],
    value_col=config['extensive_value_col'],
    top_n=config.get('top_n', 3),
    sort_by='estimate',
    asc=config.get('ascending', False),
)

report = {
    'context': config['context'],
    'intensive_margin': intensive_results,
    'extensive_margin': extensive_results,
}

output_path = Path(config['output_file'])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(report, indent=2))
PY
