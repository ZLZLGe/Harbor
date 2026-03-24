#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta, timezone


def write_telemetry_csv(path, num_sensors=8, samples_per_sensor=240, seed=0):
    rng = random.Random(seed)
    sensor_ids = [f"sensor-{index:02d}" for index in range(num_sensors)]
    base_timestamp = datetime(2025, 1, 14, 6, 0, tzinfo=timezone.utc)
    row_count = 0

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "sensor_id", "reading"])

        for sample_index in range(samples_per_sensor):
            minute_offset = sample_index * 4
            for sensor_index, sensor_id in enumerate(sensor_ids):
                timestamp = base_timestamp + timedelta(minutes=minute_offset, seconds=sensor_index * 7)
                baseline = 41.0 + sensor_index * 1.9
                wave = math.sin((sample_index + sensor_index * 2) / 7.0) * (3.2 + sensor_index * 0.08)
                drift = (sample_index % 144) * 0.018
                noise = rng.uniform(-0.35, 0.35)
                reading = baseline + wave + drift + noise

                if sample_index % 83 == 0 and sensor_index % 3 == 1:
                    reading += 8.75
                if sample_index % 127 == 0 and sensor_index % 4 == 2:
                    reading -= 7.5
                if sample_index % 211 == 0 and sensor_index == num_sensors - 1:
                    reading += 9.0

                writer.writerow(
                    [
                        timestamp.isoformat().replace("+00:00", "Z"),
                        sensor_id,
                        f"{reading:.6f}",
                    ]
                )
                row_count += 1

    return row_count
