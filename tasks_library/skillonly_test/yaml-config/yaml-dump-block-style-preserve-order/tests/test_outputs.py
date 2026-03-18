import json
from pathlib import Path

import yaml


def build_expected(payload):
    metadata = {
        'scenario_name': payload['fleet_profile']['name'],
        'locale': payload['fleet_profile']['locale'],
        'owner': payload['fleet_profile']['owner'],
        'revision': payload['fleet_profile']['revision'],
        'generated_by': 'yaml-task-builder',
    }

    services = []
    for service_id in payload['service_order']:
        service = payload['services'][service_id]
        services.append(
            {
                'id': service_id,
                'enabled': service['enabled'],
                'rollout': {
                    'strategy': service['rollout']['strategy'],
                    'batches': service['rollout']['batches'],
                },
                'endpoints': service['endpoints'],
            }
        )

    safety_limits = {key: payload['thresholds'][key] for key in payload['threshold_order']}

    notifications = []
    for item in payload['notification_templates']:
        notifications.append(
            {
                'channel': item['channel'],
                'template': item['template'],
                'recipients': item['recipients'],
            }
        )

    return {
        'metadata': metadata,
        'services': services,
        'safety_limits': safety_limits,
        'notifications': notifications,
    }


def assert_order_constraints(parsed):
    assert list(parsed.keys()) == ['metadata', 'services', 'safety_limits', 'notifications'], 'Top-level key order mismatch'

    metadata = parsed['metadata']
    assert list(metadata.keys()) == ['scenario_name', 'locale', 'owner', 'revision', 'generated_by'], 'metadata key order mismatch'

    services = parsed['services']
    assert isinstance(services, list), 'services must be a list'
    for idx, service in enumerate(services):
        assert list(service.keys()) == ['id', 'enabled', 'rollout', 'endpoints'], f'services[{idx}] key order mismatch'
        rollout = service['rollout']
        assert list(rollout.keys()) == ['strategy', 'batches'], f'services[{idx}].rollout key order mismatch'

    safety_limits = parsed['safety_limits']
    assert list(safety_limits.keys()) == ['max_lateral_error_m', 'max_brake_temp_c', 'min_sensor_score'], 'safety_limits key order mismatch'

    notifications = parsed['notifications']
    assert isinstance(notifications, list), 'notifications must be a list'
    for idx, item in enumerate(notifications):
        assert list(item.keys()) == ['channel', 'template', 'recipients'], f'notifications[{idx}] key order mismatch'


def assert_text_constraints(output_text):
    assert '\\u' not in output_text, 'Unicode text must not be escaped'

    forbidden_tokens = ['{', '}', '[', ']']
    for token in forbidden_tokens:
        assert token not in output_text, f'Found flow-style token: {token}'

    assert '华东夜航车队' in output_text, 'Missing expected unicode fleet name'
    assert '夜航巡检完成，请确认部署窗口' in output_text, 'Missing expected unicode notification text'

    assert output_text.endswith('\n'), 'Output file must end with a newline'


def main():
    input_path = Path('/root/input/deployment_payload.json')
    payload = json.loads(input_path.read_text(encoding='utf-8'))
    expected = build_expected(payload)

    output_path = Path('/root/outputs/generated_config.yaml')
    assert output_path.exists(), 'Missing /root/outputs/generated_config.yaml'

    output_text = output_path.read_text(encoding='utf-8')
    parsed = yaml.safe_load(output_text)

    assert isinstance(parsed, dict), 'YAML root must be a mapping'
    assert parsed == expected, 'Parsed YAML data mismatch'

    assert_order_constraints(parsed)
    assert_text_constraints(output_text)


if __name__ == '__main__':
    main()
