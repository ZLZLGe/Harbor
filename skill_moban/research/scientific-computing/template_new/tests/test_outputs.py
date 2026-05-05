from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, '/tests')
import reference_metrics

OUTPUT = Path('/root/output')
WORKSPACE = Path('/root/workspace')
DATA = Path('/root/data')

TREND_COLUMNS = [
    'station_id', 'station_name', 'start_date', 'end_date', 'n_days', 'valid_observations',
    'missing_rate', 'outlier_rate', 'temp_slope_c_per_year', 'p_value', 'trend_method'
]
ATTR_COLUMNS = ['category', 'contribution_pct', 'signed_effect', 'rank', 'n_features']


def read_outputs() -> dict[str, object]:
    return {
        'trends': pd.read_csv(OUTPUT / 'station_trends.csv'),
        'attribution': pd.read_csv(OUTPUT / 'driver_attribution.csv'),
        'audit': json.loads((OUTPUT / 'analysis_workflow_audit.json').read_text(encoding='utf-8')),
        'summary': json.loads((OUTPUT / 'run_summary.json').read_text(encoding='utf-8')), 
    }


def test_required_outputs_exist_and_parse() -> None:
    required = [OUTPUT / 'station_trends.csv', OUTPUT / 'driver_attribution.csv', OUTPUT / 'analysis_workflow_audit.json', OUTPUT / 'run_summary.json']
    for path in required:
        assert path.exists(), f'missing required output: {path}'
        assert path.stat().st_size > 0, f'empty required output: {path}'
    actual = read_outputs()
    assert list(actual['trends'].columns) == TREND_COLUMNS
    assert list(actual['attribution'].columns) == ATTR_COLUMNS
    assert {'dataset', 'quality_control', 'trend', 'attribution', 'warnings'}.issubset(actual['summary'])




def test_bound_data_analyst_skill_is_available_and_unchanged() -> None:
    import hashlib

    skill_path = Path('/root/.codex/skills/data-analyst/SKILL.md')
    assert skill_path.exists(), 'bound data-analyst skill is not installed in the runtime environment'
    content = skill_path.read_text(encoding='utf-8')
    assert 'name: data-analyst' in content
    assert 'SQL, pandas, and statistical analysis' in content
    assert 'Performance considerations' in content or 'Performance considerations'.lower() in content.lower()
    digest = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    assert digest == '144e82457e8861ae540138f9d0168e1eb7c56761bc8db541733d448cb7cb3e1e'

def test_analysis_workflow_audit_documents_skill_workflow() -> None:
    actual = read_outputs()
    audit = actual['audit']
    summary = actual['summary']
    attribution = actual['attribution']
    assert {'sql_queries', 'pandas_operations', 'statistical_checks', 'performance_considerations', 'example_results', 'skill_output_format', 'interpretation'}.issubset(audit)
    assert isinstance(audit['sql_queries'], list) and len(audit['sql_queries']) >= 3
    assert isinstance(audit['pandas_operations'], list) and len(audit['pandas_operations']) >= 5
    assert isinstance(audit['statistical_checks'], list) and len(audit['statistical_checks']) >= 3
    assert isinstance(audit['performance_considerations'], list) and len(audit['performance_considerations']) >= 2
    assert isinstance(audit['example_results'], list) and len(audit['example_results']) >= 3
    audit_text = json.dumps(audit, ensure_ascii=False).lower()
    for token in ['sqlite', 'join', 'merge', 'trend', 'attribution']:
        assert token in audit_text
    assert 'p-value' in audit_text or 'p_value' in audit_text or 'significance' in audit_text or 'kendall' in audit_text
    assert 'duplicate' in audit_text or 'dedup' in audit_text or 'de-dup' in audit_text or 'latest' in audit_text
    assert 'group' in audit_text or 'aggregat' in audit_text or 'daily' in audit_text
    assert any('vector' in str(item).lower() or 'determin' in str(item).lower() or 'reuse' in str(item).lower() or 'performance' in str(item).lower() for item in audit['performance_considerations'])
    examples_text = json.dumps(audit['example_results'], ensure_ascii=False).lower()
    assert 'slope' in examples_text or 'trend' in examples_text
    assert 'dominant' in examples_text or 'driver' in examples_text or 'category' in examples_text
    assert '100' in examples_text or 'contribution' in examples_text
    skill_format = audit['skill_output_format']
    assert {'clear_comments_or_notes', 'example_results', 'performance_considerations', 'interpretation_of_findings'}.issubset(skill_format)
    for key in ['clear_comments_or_notes', 'example_results', 'performance_considerations', 'interpretation_of_findings']:
        assert isinstance(skill_format[key], list) and len(skill_format[key]) >= 1
    skill_text = json.dumps(skill_format, ensure_ascii=False).lower()
    assert 'example' in skill_text or 'station=' in skill_text or 'slope' in skill_text
    assert 'performance' in skill_text or 'vector' in skill_text or 'reuse' in skill_text or 'determin' in skill_text
    assert 'interpret' in skill_text or 'finding' in skill_text or 'warming' in skill_text
    interpretation = audit['interpretation']
    assert interpretation['dominant_category'] == summary['attribution']['dominant_category']
    assert interpretation['dominant_category'] == attribution.sort_values(['rank', 'category']).iloc[0]['category']
    assert int(interpretation['warming_station_count']) == int(summary['trend']['stations_with_significant_warming'])
    assert isinstance(interpretation.get('key_findings'), list) and len(interpretation['key_findings']) >= 2

def test_station_trends_match_independent_oracle() -> None:
    expected_bundle = reference_metrics.expected_bundle()
    expected = expected_bundle['trends'].sort_values('station_id').reset_index(drop=True)
    actual = read_outputs()['trends'].sort_values('station_id').reset_index(drop=True)
    assert list(actual['station_id']) == list(expected['station_id'])
    assert list(actual['station_name']) == list(expected['station_name'])
    assert actual['trend_method'].astype(str).str.contains('theil|sen|robust|kendall|hampel', case=False, regex=True).all()
    assert actual['p_value'].between(0, 1).all()
    assert actual['temp_slope_c_per_year'].gt(0).all()
    assert actual['missing_rate'].between(0, 0.08).all()
    assert actual['outlier_rate'].between(0, 0.08).all()
    assert actual['n_days'].between(1350, 1461).all()
    assert actual['valid_observations'].between(5000, 5900).all()
    for value in actual['start_date']:
        assert re.match(r'^20\d\d-\d\d-\d\d$', str(value))
    for value in actual['end_date']:
        assert re.match(r'^20\d\d-\d\d-\d\d$', str(value))
    assert actual['temp_slope_c_per_year'].between(0.01, 1.0).all()
    assert (actual['p_value'] < 0.2).all()


def test_driver_attribution_matches_independent_oracle() -> None:
    actual = read_outputs()['attribution'].copy()
    assert set(actual['category']) == {'Heat', 'Flow', 'Wind', 'Human'}
    assert len(actual) == 4
    assert actual['contribution_pct'].ge(0).all()
    assert abs(float(actual['contribution_pct'].sum()) - 100.0) <= 1e-6
    assert set(actual['rank']) == {1, 2, 3, 4}
    feature_counts = actual.set_index('category')['n_features'].to_dict()
    assert feature_counts['Heat'] >= 2
    assert feature_counts['Flow'] >= 2
    assert feature_counts['Wind'] >= 1
    assert feature_counts['Human'] >= 2
    assert all(1 <= int(value) <= 4 for value in feature_counts.values())
    ranked = actual.sort_values(['rank', 'category']).reset_index(drop=True)
    assert ranked['contribution_pct'].is_monotonic_decreasing
    assert ranked.iloc[0]['category'] in {'Heat', 'Flow', 'Human'}
    assert actual['signed_effect'].notna().all()
    assert actual['signed_effect'].abs().sum() > 0.05
    assert actual['contribution_pct'].max() >= 25.0


def test_run_summary_is_consistent_with_outputs_and_oracle() -> None:
    expected = reference_metrics.expected_bundle()['summary']
    actual_outputs = read_outputs()
    summary = actual_outputs['summary']
    trends = actual_outputs['trends']
    attribution = actual_outputs['attribution']

    assert summary['dataset']['stations'] == expected['dataset']['stations']
    assert summary['dataset']['raw_observations'] == expected['dataset']['raw_observations']
    assert summary['dataset']['analysis_start'] == expected['dataset']['analysis_start']
    assert summary['dataset']['analysis_end'] == expected['dataset']['analysis_end']
    assert 5600 <= int(summary['dataset']['daily_records']) <= int(expected['dataset']['daily_records'])
    assert summary['quality_control']['dropped_duplicate_rows'] == expected['quality_control']['dropped_duplicate_rows']
    assert int(summary['quality_control']['dropped_qc_rows']) >= 8
    assert summary['quality_control']['dropped_event_window_rows'] >= expected['quality_control']['dropped_event_window_rows']
    assert summary['quality_control']['imputed_daily_values'] >= 0
    assert re.search(r'theil|sen|robust|kendall|hampel', str(summary['trend']['method']), re.IGNORECASE)
    assert summary['trend']['stations_with_significant_warming'] == int(((trends['temp_slope_c_per_year'] > 0) & (trends['p_value'] < 0.05)).sum())
    assert abs(float(summary['trend']['median_slope_c_per_year']) - float(trends['temp_slope_c_per_year'].median())) <= 0.004
    assert isinstance(summary['attribution']['method'], str) and len(summary['attribution']['method']) >= 8
    dominant = attribution.sort_values(['rank', 'category']).iloc[0]['category']
    assert summary['attribution']['dominant_category'] == dominant
    assert 0.0 <= float(summary['attribution']['model_r2']) <= 1.0
    assert abs(float(summary['attribution']['contribution_sum']) - 100.0) <= 1e-6
    assert isinstance(summary['warnings'], list)

def test_guardrail_uses_real_sqlite_and_preserves_inputs() -> None:
    db = DATA / 'observatory.db'
    assert db.exists() and db.stat().st_size > 100_000
    conn = reference_metrics.sqlite3.connect(db)
    try:
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)['name'].tolist()
    finally:
        conn.close()
    assert {'stations', 'water_temperature', 'weather_daily', 'hydrology_daily', 'human_activity_daily', 'maintenance_events'}.issubset(tables)
    source_files = list(WORKSPACE.rglob('*.py')) + list(WORKSPACE.rglob('*.sql'))
    joined = '\n'.join(path.read_text(encoding='utf-8', errors='ignore') for path in source_files)
    assert re.search(r'sqlite3|read_sql_query|SELECT\s+.+FROM', joined, re.IGNORECASE | re.DOTALL), 'solution does not appear to query SQLite data'
    assert not any(path.name in {'observatory.db', 'station_metadata.csv', 'event_windows.csv', 'expected_schema.json'} for path in WORKSPACE.rglob('*'))


def test_guardrail_no_hardcoded_answer_tables_or_static_shortcuts() -> None:
    source_files = list(WORKSPACE.rglob('*.py')) + list(WORKSPACE.rglob('*.sh')) + list(WORKSPACE.rglob('*.sql'))
    joined = '\n'.join(path.read_text(encoding='utf-8', errors='ignore') for path in source_files)
    assert 'naive pipeline output' not in (OUTPUT / 'run_summary.json').read_text(encoding='utf-8', errors='ignore')
    assert joined.count('North Inlet') <= 2 and joined.count('Deep Basin') <= 2, 'suspicious station-name hardcoding'
    forbidden = ['OPENAI_API_KEY', 'requests.post', 'boto3', 'google.cloud', 'azure.identity']
    assert not any(token in joined for token in forbidden), 'solution should not depend on external accounts or cloud services'
    try:
        tree = ast.parse(joined)
    except SyntaxError:
        return
    long_literal_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Dict)) and hasattr(node, 'elts') and len(getattr(node, 'elts', [])) > 20:
            long_literal_count += 1
    assert long_literal_count < 3, 'suspicious large literal answer table in code'



def test_guardrail_dynamic_event_window_rerun() -> None:
    import shutil
    import subprocess
    import sys

    original = read_outputs()['summary']
    tmp_root = Path('/tmp/lake_mutation_check')
    data_copy = tmp_root / 'data'
    output_copy = tmp_root / 'output'
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    shutil.copytree(DATA, data_copy)
    windows = pd.read_csv(data_copy / 'event_windows.csv')
    extra = pd.DataFrame([
        {
            'station_id': 'LK01',
            'start_at': '2019-02-01T00:00:00',
            'end_at': '2019-02-02T00:00:00',
            'event_type': 'mutation_qc_check',
            'exclude_from_analysis': True,
        }
    ])
    pd.concat([windows, extra], ignore_index=True).to_csv(data_copy / 'event_windows.csv', index=False)
    output_copy.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '/root/workspace/run_analysis.py', '--data', str(data_copy), '--output', str(output_copy)], check=True, timeout=120)
    mutated_summary = json.loads((output_copy / 'run_summary.json').read_text(encoding='utf-8'))
    assert mutated_summary['dataset']['raw_observations'] == original['dataset']['raw_observations']
    assert mutated_summary['quality_control']['dropped_event_window_rows'] > original['quality_control']['dropped_event_window_rows']
    assert mutated_summary['dataset']['daily_records'] < original['dataset']['daily_records']
    assert (output_copy / 'analysis_workflow_audit.json').exists()

def test_guardrail_repeated_run_is_deterministic() -> None:
    before = {
        path.name: path.read_bytes()
        for path in [OUTPUT / 'station_trends.csv', OUTPUT / 'driver_attribution.csv', OUTPUT / 'analysis_workflow_audit.json', OUTPUT / 'run_summary.json']
    }
    import subprocess
    import sys
    subprocess.run([sys.executable, '/root/workspace/run_analysis.py', '--data', '/root/data', '--output', '/root/output'], check=True, timeout=120)
    after = {
        path.name: path.read_bytes()
        for path in [OUTPUT / 'station_trends.csv', OUTPUT / 'driver_attribution.csv', OUTPUT / 'analysis_workflow_audit.json', OUTPUT / 'run_summary.json']
    }
    assert before == after
