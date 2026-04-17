import json
import os


def test_outputs() -> None:
    workspace_root = os.environ.get('WORKSPACE_ROOT', '/app/workspace')
    output_path = os.path.join(workspace_root, 'output', 'control_bundle.json')
    assert os.path.exists(output_path), f'缺少输出文件: {output_path}'

    with open(output_path, 'r', encoding='utf-8') as f:
        actual = json.load(f)

    expected = {
        'summary': {
            'total_services': 4,
            'failed_services': 3,
        },
        'services': [
            {
                'name': 'alpha-api',
                'namespace': 'payments',
                'status': 'pass',
                'rotation_priority': 'normal',
                'violations': [],
            },
            {
                'name': 'beta-worker',
                'namespace': 'ops',
                'status': 'fail',
                'rotation_priority': 'urgent',
                'violations': ['mtls_missing', 'weak_secret_store', 'cert_rotation_urgent'],
            },
            {
                'name': 'delta-sync',
                'namespace': 'shared',
                'status': 'fail',
                'rotation_priority': 'normal',
                'violations': ['network_open'],
            },
            {
                'name': 'gamma-gateway',
                'namespace': 'edge',
                'status': 'fail',
                'rotation_priority': 'urgent',
                'violations': ['mtls_missing', 'network_open', 'cert_rotation_urgent'],
            },
        ],
    }

    assert actual == expected, f'输出内容不匹配.\nactual={actual}\nexpected={expected}'

    names = [service['name'] for service in actual['services']]
    assert names == sorted(names), f'services 未按 name 升序排序: {names}'

    for service in actual['services']:
        assert service['status'] in {'pass', 'fail'}, f'非法 status: {service["status"]}'
        assert service['rotation_priority'] in {'normal', 'urgent'}, f'非法 rotation_priority: {service["rotation_priority"]}'
        assert isinstance(service['violations'], list), 'violations 必须为数组'
