import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get('WORKSPACE_ROOT', '/app/workspace')
    output_path = os.path.join(workspace_root, 'output', 'remediation_queue.csv')
    assert os.path.exists(output_path), f'缺少输出文件: {output_path}'

    with open(output_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames

    expected_headers = ['finding_key', 'severity', 'scanner', 'owner_team', 'sla_days', 'fix_version']
    assert headers == expected_headers, f'输出列不匹配: {headers}'

    expected_rows = [
        {
            'finding_key': 'CVE-2024-0001',
            'severity': 'critical',
            'scanner': 'deps',
            'owner_team': 'appsec',
            'sla_days': '3',
            'fix_version': '2.4.1',
        },
        {
            'finding_key': 'API-7',
            'severity': 'high',
            'scanner': 'api',
            'owner_team': 'backend',
            'sla_days': '7',
            'fix_version': '2026.04',
        },
        {
            'finding_key': 'PT-9',
            'severity': 'medium',
            'scanner': 'pentest',
            'owner_team': 'cloudsec',
            'sla_days': '30',
            'fix_version': '',
        },
        {
            'finding_key': 'OPS-2',
            'severity': 'low',
            'scanner': 'iac',
            'owner_team': 'platform',
            'sla_days': '90',
            'fix_version': 'n/a',
        },
    ]
    assert rows == expected_rows, f'输出内容不匹配.\nactual={rows}\nexpected={expected_rows}'

    severity_rank = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_rows = sorted(rows, key=lambda row: (severity_rank[row['severity']], row['finding_key']))
    assert rows == sorted_rows, '输出未按 severity 从高到低、finding_key 升序排序'

    for row in rows:
        assert row['sla_days'] in {'3', '7', '30', '90'}, f"非法 sla_days: {row['sla_days']}"
        for value in row.values():
            assert value not in {'null', 'None', 'nan', 'NaN'}, f'存在非法空值表示: {value}'


if __name__ == '__main__':
    test_outputs()
