#!/bin/bash
set -euo pipefail

python3 <<'PY'
from pathlib import Path

code = """import csv
import math
from pathlib import Path

import yaml


ROOT = Path('/root')


def load_yaml(path):
    with path.open('r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def clamp(value, low, high):
    return max(low, min(high, value))


def segment_for_time(t, segments):
    for index, segment in enumerate(segments):
        is_last = index == len(segments) - 1
        if segment['start_s'] <= t and (t < segment['end_s'] or (is_last and t <= segment['end_s'])):
            return segment
    raise ValueError(f'No segment covers t={t}')


def lead_state(t, segments):
    segment = segment_for_time(t, segments)
    span = segment['end_s'] - segment['start_s']
    ratio = 0.0 if span == 0 else (t - segment['start_s']) / span
    ratio = clamp(ratio, 0.0, 1.0)
    lead_speed = segment['start_speed_mps'] + (segment['end_speed_mps'] - segment['start_speed_mps']) * ratio
    lead_visible = 1 if segment['visible'] else 0
    return lead_visible, lead_speed


def simulate():
    config = load_yaml(ROOT / 'scenario_config.yaml')
    schedule = load_yaml(ROOT / 'lead_schedule.yaml')
    segments = schedule['segments']

    duration = config['simulation']['duration_s']
    dt = config['simulation']['dt']
    steps = int(round(duration / dt)) + 1

    ego_position = config['simulation']['initial_ego_position_m']
    ego_speed = config['simulation']['initial_ego_speed_mps']
    lead_position = config['lead_vehicle']['initial_position_m']

    rows = []
    for step in range(steps):
        t = round(step * dt, 10)
        lead_visible, lead_speed = lead_state(t, segments)
        gap = lead_position - ego_position
        safe_gap = config['gap_policy']['min_gap_m'] + config['gap_policy']['headway_s'] * ego_speed
        relative_speed = ego_speed - lead_speed
        ttc = math.inf if relative_speed <= 0 else gap / relative_speed

        if lead_visible == 0:
            mode = 'cruise'
        elif gap <= config['mode_thresholds']['emergency_factor'] * safe_gap or ttc < config['gap_policy']['emergency_ttc_s']:
            mode = 'emergency'
        elif gap <= config['mode_thresholds']['follow_factor'] * safe_gap:
            mode = 'follow'
        else:
            mode = 'cruise'

        if mode == 'cruise':
            acceleration_cmd = config['controller']['cruise_gain'] * (config['simulation']['target_speed_mps'] - ego_speed)
        elif mode == 'follow':
            acceleration_cmd = (
                config['controller']['follow_gap_gain'] * (gap - safe_gap)
                + config['controller']['follow_speed_gain'] * (lead_speed - ego_speed)
            )
        else:
            acceleration_cmd = config['vehicle']['max_brake_mps2']

        acceleration_cmd = clamp(
            acceleration_cmd,
            config['vehicle']['max_brake_mps2'],
            config['vehicle']['max_accel_mps2'],
        )

        rows.append(
            {
                'time': t,
                'lead_visible': lead_visible,
                'ego_position_m': ego_position,
                'ego_speed_mps': ego_speed,
                'lead_position_m': lead_position,
                'lead_speed_mps': lead_speed,
                'gap_m': gap,
                'safe_gap_m': safe_gap,
                'ttc_s': ttc,
                'mode': mode,
                'acceleration_cmd_mps2': acceleration_cmd,
            }
        )

        if step == steps - 1:
            continue

        next_time = round((step + 1) * dt, 10)
        _, next_lead_speed = lead_state(next_time, segments)

        ego_position = ego_position + ego_speed * dt + 0.5 * acceleration_cmd * dt * dt
        ego_speed = clamp(
            ego_speed + acceleration_cmd * dt,
            0.0,
            config['vehicle']['max_speed_mps'],
        )
        lead_position = lead_position + 0.5 * (lead_speed + next_lead_speed) * dt

    output_path = ROOT / 'stop_go_gap_results.csv'
    fieldnames = [
        'time',
        'lead_visible',
        'ego_position_m',
        'ego_speed_mps',
        'lead_position_m',
        'lead_speed_mps',
        'gap_m',
        'safe_gap_m',
        'ttc_s',
        'mode',
        'acceleration_cmd_mps2',
    ]
    with output_path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    simulate()
"""

target = Path('/root/gap_assist.py')
target.write_text(code, encoding='utf-8')
PY

python3 /root/gap_assist.py
