#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json

INPUT_FILE = "/root/campus_cooling_snapshot.json"
OUTPUT_FILE = "/root/cooling_dispatch_summary.json"


def round4(value):
    return round(float(value), 4)


def solve_energy_dispatch(snapshot):
    chillers = snapshot["chillers"]
    target_load = float(snapshot["cooling_load_RT"])

    min_total = sum(float(chiller["cooling_min_RT"]) for chiller in chillers)
    max_total = sum(float(chiller["cooling_max_RT"]) for chiller in chillers)
    if not (min_total <= target_load <= max_total):
        raise ValueError("Cooling load is outside aggregate feasible range")

    def clipped_output(lambda_value, chiller):
        quadratic = float(chiller["quadratic_power_kW_per_RT2"])
        linear = float(chiller["linear_power_kW_per_RT"])
        lower = float(chiller["cooling_min_RT"])
        upper = float(chiller["cooling_max_RT"])
        target = (lambda_value - linear) / (2.0 * quadratic)
        return min(upper, max(lower, target))

    low = min(
        float(chiller["linear_power_kW_per_RT"])
        + 2.0 * float(chiller["quadratic_power_kW_per_RT2"]) * float(chiller["cooling_min_RT"])
        for chiller in chillers
    ) - 10.0
    high = max(
        float(chiller["linear_power_kW_per_RT"])
        + 2.0 * float(chiller["quadratic_power_kW_per_RT2"]) * float(chiller["cooling_max_RT"])
        for chiller in chillers
    ) + 10.0

    for _ in range(200):
        midpoint = (low + high) / 2.0
        scheduled = sum(clipped_output(midpoint, chiller) for chiller in chillers)
        if scheduled < target_load:
            low = midpoint
        else:
            high = midpoint

    lambda_value = (low + high) / 2.0
    outputs = [clipped_output(lambda_value, chiller) for chiller in chillers]

    load_gap = target_load - sum(outputs)
    if abs(load_gap) > 1e-7:
        adjustable = [
            idx
            for idx, (output, chiller) in enumerate(zip(outputs, chillers))
            if float(chiller["cooling_min_RT"]) + 1e-7 < output < float(chiller["cooling_max_RT"]) - 1e-7
        ]
        if not adjustable:
            raise ValueError("Unable to close residual load gap")
        share = load_gap / len(adjustable)
        for idx in adjustable:
            outputs[idx] += share

    return outputs


def allocate_reserve(snapshot, outputs):
    chillers = snapshot["chillers"]
    reserve_requirement = float(snapshot["spinning_reserve_requirement_RT"])
    remaining = reserve_requirement
    reserves = [0.0] * len(chillers)
    reserve_stack_order = []

    order = sorted(
        range(len(chillers)),
        key=lambda idx: (int(chillers[idx]["reserve_priority"]), idx),
    )

    for idx in order:
        chiller = chillers[idx]
        headroom = float(chiller["cooling_max_RT"]) - outputs[idx]
        available = min(float(chiller["reserve_max_RT"]), max(0.0, headroom))
        assigned = min(available, remaining)
        reserves[idx] = assigned
        if assigned > 1e-7:
            reserve_stack_order.append(chiller["chiller_id"])
        remaining -= assigned
        if remaining <= 1e-7:
            break

    if remaining > 1e-7:
        raise ValueError("Insufficient reserve headroom")

    return reserves, reserve_stack_order


def build_report(snapshot):
    chillers = snapshot["chillers"]
    price = float(snapshot["electricity_price_dollars_per_kWh"])

    outputs = solve_energy_dispatch(snapshot)
    reserves, reserve_stack_order = allocate_reserve(snapshot, outputs)

    chiller_dispatch = []
    plant_rollup = {}
    total_power = 0.0
    total_reserve = 0.0
    remaining_margin = 0.0

    for chiller, output, reserve in zip(chillers, outputs, reserves):
        power_draw = (
            float(chiller["no_load_power_kW"])
            + float(chiller["linear_power_kW_per_RT"]) * output
            + float(chiller["quadratic_power_kW_per_RT2"]) * output * output
        )
        unused_capacity = float(chiller["cooling_max_RT"]) - output - reserve

        total_power += power_draw
        total_reserve += reserve
        remaining_margin += unused_capacity

        chiller_dispatch.append(
            {
                "chiller_id": chiller["chiller_id"],
                "plant": chiller["plant"],
                "cooling_output_RT": round4(output),
                "spinning_reserve_RT": round4(reserve),
                "power_draw_kW": round4(power_draw),
                "available_capacity_RT": round4(chiller["cooling_max_RT"]),
                "unused_capacity_RT": round4(unused_capacity),
            }
        )

        bucket = plant_rollup.setdefault(
            chiller["plant"],
            {"cooling_output_RT": 0.0, "spinning_reserve_RT": 0.0, "unused_capacity_RT": 0.0},
        )
        bucket["cooling_output_RT"] += output
        bucket["spinning_reserve_RT"] += reserve
        bucket["unused_capacity_RT"] += unused_capacity

    summary = {
        "cooling_load_RT": round4(snapshot["cooling_load_RT"]),
        "scheduled_cooling_RT": round4(sum(outputs)),
        "spinning_reserve_requirement_RT": round4(snapshot["spinning_reserve_requirement_RT"]),
        "scheduled_spinning_reserve_RT": round4(total_reserve),
        "total_power_kW": round4(total_power),
        "total_electricity_cost_dollars_per_hour": round4(total_power * price),
        "remaining_margin_RT": round4(remaining_margin),
    }

    report = {
        "campus_id": snapshot["campus_id"],
        "operating_interval": snapshot["operating_interval"],
        "chiller_dispatch": chiller_dispatch,
        "summary": summary,
        "plant_rollup": [
            {
                "plant": plant,
                "cooling_output_RT": round4(values["cooling_output_RT"]),
                "spinning_reserve_RT": round4(values["spinning_reserve_RT"]),
                "unused_capacity_RT": round4(values["unused_capacity_RT"]),
            }
            for plant, values in sorted(plant_rollup.items())
        ],
        "reserve_stack_order": reserve_stack_order,
    }
    return report


with open(INPUT_FILE, encoding="utf-8") as f:
    snapshot = json.load(f)

report = build_report(snapshot)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
PY
